# ============================================================
# HASFLO PINTEREST - SCRAPER
# Pendekatan: Network Interception + Fallback Selector Generik
# Video: input manual (tidak bisa di-scrape dari Shopee headless)
#
# UPDATE (29 Juni 2026): Ditambahkan stealth patch karena Shopee
# mulai mendeteksi navigator.webdriver dan fingerprint headless
# Playwright, lalu meredirect ke wall verifikasi traffic/login
# (https://shopee.co.id/verify/traffic/error?...&is_logged_in=false).
#
# CATATAN PENTING: stealth patch ini menyamarkan fingerprint browser
# (navigator.webdriver, plugins, dll) supaya TERLIHAT seperti browser
# manusia biasa. Tapi kalau wall login Shopee ternyata murni berbasis
# status sesi (is_logged_in=false) dan bukan cuma fingerprint check,
# patch ini TIDAK AKAN cukup -- baca pesan error 'LOGIN_WALL_DETECTED'
# di hasil scraping untuk tahu apakah ini masih terjadi.
# ============================================================

import re
import asyncio
from playwright.async_api import async_playwright


def clean_image_url(url: str) -> str:
    """Hapus semua suffix @resize_xxx untuk dapat resolusi tertinggi."""
    url = re.sub(r'@resize_[^.]+', '', url)
    return url.split('?')[0]


def is_valid_product_image(url: str) -> bool:
    """Filter URL gambar produk yang valid."""
    if 'susercontent.com/file/' not in url:
        return False
    if not url.endswith('.webp'):
        return False
    # Skip thumbnail video
    if '_cover' in url or '_tn' in url:
        return False
    excluded = ['avatar', 'icon', 'logo', 'banner', 'shop']
    if any(x in url.lower() for x in excluded):
        return False
    return True


def clean_description(raw: str) -> str:
    if not raw:
        return ''
    blacklist = [
        'terlaris', 'best seller', 'bestseller', 'garansi', 'gratis ongkir',
        'cod', 'flash sale', 'diskon', 'promo', 'limited', 'stok terbatas',
        'buruan', 'segera', 'order sekarang', 'beli sekarang', 'checkout',
        'tokopedia', 'shopee', 'lazada', 'rating', 'ulasan', 'review',
        'follow', 'like', 'share', 'klik', 'whatsapp', 'wa kami',
    ]
    lines = raw.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(bl in line.lower() for bl in blacklist):
            continue
        if re.match(r'^[\W\d]+$', line):
            continue
        cleaned_lines.append(line)
    result = ' '.join(cleaned_lines[:3])
    if len(result) > 450:
        result = result[:447] + '...'
    return result


# ============================================================
# STEALTH INIT SCRIPT
# Dijalankan SEBELUM script halaman manapun, supaya properti
# fingerprint browser sudah "dipoles" sejak awal load.
# Patch ini menutup celah deteksi headless paling umum:
#   - navigator.webdriver
#   - navigator.plugins kosong
#   - navigator.languages kosong/tidak konsisten
#   - window.chrome tidak ada (khas headless Chromium)
#   - permissions API yang bocor
#   - WebGL renderer yang menunjukkan SwiftShader (software render headless)
# ============================================================

STEALTH_INIT_SCRIPT = """
// 1. Hilangkan navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// 2. Palsukan navigator.plugins supaya tidak kosong (ciri khas headless)
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
        { name: 'Native Client', filename: 'internal-nacl-plugin' },
    ]
});

// 3. Pastikan navigator.languages konsisten dengan locale id-ID
Object.defineProperty(navigator, 'languages', {
    get: () => ['id-ID', 'id', 'en-US', 'en']
});

// 4. window.chrome harus ada (headless Chromium defaultnya tidak punya ini)
window.chrome = window.chrome || { runtime: {} };

// 5. Patch permissions.query supaya tidak membocorkan status headless
const originalQuery = window.navigator.permissions ? window.navigator.permissions.query : null;
if (originalQuery) {
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: 'default' })
            : originalQuery(parameters)
    );
}

// 6. Samarkan WebGL renderer (SwiftShader = sinyal kuat headless)
const getParameterProto = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';            // UNMASKED_VENDOR_WEBGL
    if (parameter === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
    return getParameterProto.call(this, parameter);
};

// 7. navigator.hardwareConcurrency & deviceMemory yang realistis
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
"""

# User-Agent Chrome versi terbaru (per Juni 2026). UA yang stale/lawas
# adalah sinyal tambahan yang dicurigai sistem anti-bot.
MODERN_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/126.0.0.0 Safari/537.36'
)


def detect_login_wall(current_url: str, page_text: str) -> bool:
    """
    Deteksi apakah kita diredirect ke wall verifikasi traffic / login Shopee.
    Pola yang dikonfirmasi dari debug log: redirect ke domain shopee.co.id
    (bukan s.shopee.co.id) dengan path /verify/traffic/error dan/atau
    parameter is_logged_in=false, ATAU teks "belum masuk" / "Log In" muncul
    sebagai konten utama halaman.
    """
    url_lower = current_url.lower()
    if '/verify/traffic' in url_lower or 'is_logged_in=false' in url_lower:
        return True
    text_lower = (page_text or '').lower()
    login_wall_phrases = [
        'sepertinya anda belum masuk',
        'halaman tidak tersedia',
    ]
    return any(phrase in text_lower for phrase in login_wall_phrases)


async def scrape_shopee_product(url: str) -> dict:
    result = {
        'judul': '',
        'deskripsi': '',
        'images': [],   # list dict: {'url': str, 'type': 'image', 'thumbnail': ''}
        'error': None
    }

    try:
        async with async_playwright() as p:
            # --headless=new dipakai karena rendering pathnya lebih dekat ke
            # Chrome asli dibanding mode headless lama, sehingga beberapa
            # fingerprint check (terutama yang terkait rendering) lebih sulit
            # membedakannya dari browser biasa.
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--headless=new',
                ],
            )
            context = await browser.new_context(
                user_agent=MODERN_USER_AGENT,
                locale='id-ID',
                timezone_id='Asia/Jakarta',
                viewport={'width': 1366, 'height': 768},
            )

            # Suntikkan stealth script SEBELUM halaman apapun dimuat
            await context.add_init_script(STEALTH_INIT_SCRIPT)

            page = await context.new_page()

            # ------------------------------------------------
            # NETWORK INTERCEPTION — gambar saja
            # ------------------------------------------------
            image_urls = set()

            async def handle_response(response):
                try:
                    resp_url = response.url
                    if 'susercontent.com/file/' in resp_url and '.webp' in resp_url:
                        clean = clean_image_url(resp_url)
                        if is_valid_product_image(clean):
                            image_urls.add(clean)
                except Exception:
                    pass

            page.on('response', handle_response)

            # ------------------------------------------------
            # LOAD HALAMAN
            # ------------------------------------------------
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)

            # ------------------------------------------------
            # CEK WALL LOGIN / VERIFIKASI TRAFFIC
            # Kalau kena wall ini, tidak ada gunanya lanjut ke langkah
            # berikutnya -- DOM produk memang tidak akan pernah muncul.
            # ------------------------------------------------
            current_url = page.url
            body_text = await page.evaluate('() => document.body.innerText')

            if detect_login_wall(current_url, body_text):
                result['error'] = (
                    "LOGIN_WALL_DETECTED: Shopee meredirect ke halaman verifikasi "
                    "traffic/login (bukan halaman produk). Stealth patch fingerprint "
                    "tidak cukup untuk melewati ini -- kemungkinan perlu sesi browser "
                    "yang sudah login (lihat opsi cookie/storage_state). "
                    f"URL redirect: {current_url}"
                )
                print(f"[SCRAPER] !! {result['error']}")
                await browser.close()
                return result

            # Tutup popup bahasa
            try:
                for btn_text in ['Bahasa Indonesia', 'Indonesia']:
                    btn = page.get_by_text(btn_text, exact=True)
                    if await btn.count() > 0:
                        await btn.first.click()
                        print("[SCRAPER] Popup bahasa ditutup")
                        await asyncio.sleep(2)
                        break
            except Exception:
                pass

            await asyncio.sleep(2)

            # ------------------------------------------------
            # AMBIL JUDUL
            # ------------------------------------------------
            try:
                judul_el = await page.query_selector('h1')
                if judul_el:
                    result['judul'] = (await judul_el.inner_text()).strip()
                    print(f"[SCRAPER] Judul: {result['judul'][:60]}")
            except Exception:
                pass

            # ------------------------------------------------
            # AMBIL DESKRIPSI
            # ------------------------------------------------
            try:
                for sel in ['div[class*="product-detail"]', 'div[class*="description"]', 'div[class*="detail"]']:
                    desc_el = await page.query_selector(sel)
                    if desc_el:
                        raw_desc = (await desc_el.inner_text()).strip()
                        result['deskripsi'] = clean_description(raw_desc)
                        break
            except Exception:
                pass

            # ------------------------------------------------
            # SCROLL untuk trigger lazy load
            # ------------------------------------------------
            await page.evaluate('window.scrollTo(0, 400)')
            await asyncio.sleep(1)
            await page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(1)

            # ------------------------------------------------
            # KLIK THUMBNAIL
            # ------------------------------------------------
            thumbnail_selectors = [
                'picture img[loading="lazy"]',
                'div[id*="pdp"] picture img',
                'section picture img',
                'img[loading="lazy"][src*="susercontent"]',
            ]

            thumbnails = []
            for sel in thumbnail_selectors:
                thumbnails = await page.query_selector_all(sel)
                if thumbnails:
                    print(f"[SCRAPER] Thumbnail match: '{sel}' — {len(thumbnails)} item")
                    break

            for i, thumb in enumerate(thumbnails):
                try:
                    await thumb.scroll_into_view_if_needed()
                    await thumb.click()
                    await asyncio.sleep(0.7)
                    print(f"[SCRAPER] Klik thumbnail {i+1}")
                except Exception as e:
                    print(f"[SCRAPER] Skip thumbnail {i+1}: {e}")

            # ------------------------------------------------
            # KLIK VARIAN WARNA
            # ------------------------------------------------
            variant_selectors = [
                'button[aria-label][aria-disabled="false"]',
                'button[aria-label][aria-disabled]',
                'div[class*="variation"] button',
            ]

            variants = []
            for sel in variant_selectors:
                variants = await page.query_selector_all(sel)
                if variants:
                    print(f"[SCRAPER] Varian match: '{sel}' — {len(variants)} item")
                    break

            for i, variant in enumerate(variants):
                try:
                    label = await variant.get_attribute('aria-label') or f'varian-{i+1}'
                    await variant.click()
                    print(f"[SCRAPER] Klik varian: {label}")
                    await asyncio.sleep(1)
                    for thumb in thumbnails:
                        try:
                            await thumb.click()
                            await asyncio.sleep(0.5)
                        except Exception:
                            pass
                except Exception as e:
                    print(f"[SCRAPER] Skip varian {i+1}: {e}")

            # ------------------------------------------------
            # BACKUP DOM — gambar
            # ------------------------------------------------
            all_imgs = await page.query_selector_all('img[src*="susercontent.com"]')
            for img in all_imgs:
                try:
                    src = await img.get_attribute('src')
                    if src:
                        clean = clean_image_url(src)
                        if is_valid_product_image(clean):
                            image_urls.add(clean)
                except Exception:
                    pass

            await asyncio.sleep(2)

            result['images'] = [
                {'url': u, 'type': 'image', 'thumbnail': ''}
                for u in sorted(image_urls)
            ]
            print(f"[SCRAPER] Total gambar: {len(result['images'])}")

            await browser.close()

    except Exception as e:
        result['error'] = str(e)
        print(f"[SCRAPER] ERROR: {e}")

    return result


def scrape_product(url: str) -> dict:
    return asyncio.run(scrape_shopee_product(url))

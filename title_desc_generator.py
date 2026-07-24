# ============================================================
# HASFLO PINTEREST - TITLE & DESCRIPTION GENERATOR
# Section Streamlit: judul terformat + SEO description
# Pakai Gemini API (google-genai) — konsisten dengan processor.py
# ============================================================
#
# CARA INTEGRASI KE app.py:
# 1. Import fungsi ini di bagian atas app.py:
#       from title_desc_generator import render_title_desc_section
# 2. Panggil setelah blok Step 1 (setelah st.divider() pertama):
#       render_title_desc_section()
#
# ============================================================

import json
import re
import os
import streamlit as st

# ============================================================
# KONSTANTA LABEL TIPE PRODUK (label tampilan Pinterest)
# ============================================================

PRODUCT_TYPE_LABELS = {
    "dress":   "Dress",
    "blouse":  "Blouse",
    "tunik":   "Tunik",
    "outer":   "Outer",
    "setelan": "Setelan",
    "unknown": "Busana",
}

# ============================================================
# SEO KEYWORDS — load dari seo_keywords.json
# Fallback ke hardcoded kalau file tidak ditemukan / corrupt
# ============================================================

SEO_KEYWORDS_DEFAULT = {
    "dress": {
        "title": ["dress motif bunga", "floral dress wanita", "outfit kondangan motif bunga"],
        "description": ["OOTD dress motif bunga", "inspirasi outfit dress floral", "fashion wanita motif bunga"],
    },
    "blouse": {
        "title": ["blouse motif bunga", "floral blouse wanita", "atasan bunga wanita"],
        "description": ["OOTD blouse motif bunga", "inspirasi outfit blouse floral", "fashion atasan motif bunga"],
    },
    "tunik": {
        "title": ["tunik motif bunga", "floral tunik wanita", "tunik bunga muslimah"],
        "description": ["OOTD tunik motif bunga", "inspirasi outfit tunik floral", "fashion muslimah motif bunga"],
    },
    "outer": {
        "title": ["outer motif bunga", "floral outer wanita", "cardigan bunga wanita"],
        "description": ["OOTD outer motif bunga", "inspirasi outfit outer floral", "fashion outer motif bunga"],
    },
    "setelan": {
        "title": ["setelan motif bunga", "floral setelan wanita", "co-ord set motif bunga"],
        "description": ["OOTD setelan motif bunga", "inspirasi outfit setelan floral", "fashion setelan motif bunga"],
    },
    "unknown": {
        "title": ["floral fashion wanita", "pakaian motif bunga", "outfit floral casual"],
        "description": ["OOTD floral fashion", "inspirasi outfit motif bunga", "fashion wanita Indonesia"],
    },
}


def load_seo_keywords() -> dict:
    """
    Load SEO keywords dari seo_keywords.json di root project.
    Fallback ke SEO_KEYWORDS_DEFAULT kalau file tidak ada atau corrupt.
    """
    json_path = os.path.join(os.path.dirname(__file__), "seo_keywords.json")
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        keywords = data.get("keywords", {})
        # Validasi minimal: semua tipe harus ada
        required = {"dress", "blouse", "tunik", "outer", "setelan", "unknown"}
        if not required.issubset(keywords.keys()):
            raise ValueError("seo_keywords.json tidak lengkap — fallback ke default")
        return keywords
    except Exception as e:
        print(f"[seo_keywords] Load gagal: {e} — pakai default")
        return SEO_KEYWORDS_DEFAULT


# Load sekali saat modul diimport
SEO_KEYWORDS = load_seo_keywords()


def get_seo_title_keywords(product_type: str) -> list:
    """Ambil keyword untuk generate judul Pinterest."""
    return SEO_KEYWORDS.get(product_type, SEO_KEYWORDS["unknown"]).get("title", [])


def get_seo_desc_keywords(product_type: str) -> list:
    """Ambil keyword untuk generate deskripsi Pinterest."""
    return SEO_KEYWORDS.get(product_type, SEO_KEYWORDS["unknown"]).get("description", [])


# ============================================================
# HELPER: FORMAT JUDUL PINTEREST (template — tanpa AI)
# ============================================================

def format_pinterest_title(judul_shopee: str, product_type: str) -> str:
    """
    Format: [Jenis Produk] Motif [X] Floral
    Hasil max 100 karakter, natural, tidak hard selling.
    """
    label = PRODUCT_TYPE_LABELS.get(product_type, "Busana")

    motif_match = re.search(
        r'(motif|bunga|floral|bermotif|print)\s+([\w\s\-]+?)(?:\s*[-|/,]|$)',
        judul_shopee,
        re.IGNORECASE,
    )

    if motif_match:
        motif_raw = motif_match.group(2).strip().title()
        noise = {'wanita', 'cantik', 'terbaru', 'murah', 'premium', 'import', 'best'}
        motif_words = [w for w in motif_raw.split() if w.lower() not in noise]
        motif = ' '.join(motif_words[:3])
        title = f"{label} Motif {motif} Floral"
    else:
        stopwords = {
            'wanita', 'baju', 'pakaian', 'fashion', 'terbaru', 'murah',
            'import', 'premium', 'cantik', 'best', 'seller', 'shopee',
            'ori', 'original', 'kualitas', 'berkualitas', 'ready', 'stok',
            'free', 'ongkir', 'cod', 'new', 'arrival', 'koleksi',
        }
        words = judul_shopee.split()
        meaningful = [w.title() for w in words if w.lower() not in stopwords and len(w) > 2]
        extra = ' '.join(meaningful[:4])
        title = f"{label} Floral {extra}".strip()

    if len(title) > 100:
        title = title[:97] + "..."
    return title


# ============================================================
# GENERATE DESCRIPTION (template fallback — tanpa AI)
# ============================================================

def generate_description_template(
    judul_shopee: str,
    product_type: str,
    title_formatted: str,
) -> str:
    """
    Generate description template:
    - Kalimat 1: judul asli produk VERBATIM (tidak dibersihkan)
    - Kalimat 2-4: SEO Pinterest dengan keyword per tipe dari seo_keywords.json
    """
    desc_keywords = get_seo_desc_keywords(product_type)

    kw1 = desc_keywords[0] if len(desc_keywords) > 0 else "OOTD motif bunga"
    kw2 = desc_keywords[1] if len(desc_keywords) > 1 else "inspirasi outfit floral"
    kw3 = desc_keywords[2] if len(desc_keywords) > 2 else "fashion wanita Indonesia"
    kw4 = desc_keywords[3] if len(desc_keywords) > 3 else "outfit bunga cantik"
    kw_tail = " | ".join(desc_keywords[4:7]) if len(desc_keywords) > 4 else "Pinterest fashion"

    desc = (
        f"{judul_shopee}. "
        f"{kw1} dengan desain anggun dan feminin, cocok untuk berbagai kesempatan. "
        f"Temukan inspirasi {kw2} dan {kw3} terbaik untuk tampil stylish setiap hari. "
        f"{kw4} | {kw_tail}."
    )

    if len(desc) > 500:
        desc = desc[:497] + "..."
    return desc


# ============================================================
# AI GENERATE via Gemini API (google-genai SDK)
# Konsisten dengan processor.py
# ============================================================

def ai_generate_title_desc(
    judul_shopee: str,
    desc_shopee: str,
    product_type: str,
    ai_api_key: str,
    ai_model: str,
) -> dict:
    """
    Panggil Gemini API untuk generate title + description.
    Return: {'title': str, 'description': str} atau {'error': str}
    """
    try:
        from google import genai

        client = genai.Client(api_key=ai_api_key)

        label = PRODUCT_TYPE_LABELS.get(product_type, "Busana")
        title_kws = ", ".join(get_seo_title_keywords(product_type)[:6])
        desc_kws  = ", ".join(get_seo_desc_keywords(product_type)[:6])

        prompt = f"""Kamu adalah asisten konten Pinterest untuk akun fashion wanita motif bunga.

Judul asli produk Shopee: {judul_shopee}
Deskripsi asli: {desc_shopee or "(tidak ada)"}
Tipe produk: {product_type} ({label})
Keyword SEO untuk JUDUL: {title_kws}
Keyword SEO untuk DESKRIPSI: {desc_kws}

TUGAS 1 — JUDUL Pinterest (max 100 karakter):
- Bebas kreatif, ikut keyword trending dari daftar keyword judul di atas
- Natural, tidak hard-selling, campuran Indonesia-Inggris boleh
- Harus mencerminkan tipe produk "{label}"

TUGAS 2 — DESKRIPSI Pinterest (max 500 karakter):
- Kalimat PERTAMA WAJIB: salin judul asli produk Shopee APA ADANYA — VERBATIM, tidak diubah, tidak disingkat, tidak dibersihkan
- Kalimat KEDUA WAJIB: harus mengandung kata "OOTD" dan "motif bunga"
- Kalimat 3-4: masukkan minimal 3 keyword dari daftar keyword deskripsi secara natural
- Seluruh deskripsi: Bahasa Indonesia, faktual, deskriptif
- DILARANG: "dapatkan sekarang", "segera beli", "klik link", "harga spesial", "promo", atau kata ajakan beli apapun

Output HANYA JSON (tanpa markdown backtick):
{{"title": "...", "description": "..."}}"""

        response = client.models.generate_content(model=ai_model, contents=prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)

        if "title" not in data or "description" not in data:
            raise ValueError("Response JSON tidak lengkap")

        data["title"] = data["title"][:100]
        data["description"] = data["description"][:500]

        return data

    except Exception as e:
        return {"error": str(e)}


# ============================================================
# RENDER SECTION — dipanggil dari app.py
# ============================================================

def render_title_desc_section():
    """
    Tampilkan section 'Judul & Deskripsi Pinterest' setelah scraping.
    """
    scraped_data = st.session_state.get("scraped_data", {})
    if not scraped_data:
        return

    from processor import detect_product_type

    try:
        from config import AI_ENABLED, AI_API_KEY, AI_MODEL
        has_ai = AI_ENABLED and bool(AI_API_KEY)
    except ImportError:
        has_ai = False
        AI_API_KEY = ""
        AI_MODEL = "gemini-2.5-flash-lite"

    st.divider()
    st.header("✏️ Judul & Deskripsi Pinterest")
    st.caption(
        "Judul Pinterest-ready dan deskripsi SEO-optimized dari hasil scraping. "
        "Edit langsung di kotak teks, lalu copy via ikon di pojok kanan atas kotak abu-abu."
    )

    if has_ai:
        st.success(f"✅ AI aktif ({AI_MODEL}) — judul dan deskripsi di-generate oleh Gemini")
    else:
        st.info("ℹ️ Mode template — AI tidak aktif (set AI_ENABLED=True di config.py)")

    for prod_url, data in scraped_data.items():
        judul_asli = data.get("judul", "")
        desc_asli = data.get("deskripsi", "")
        if not judul_asli:
            continue

        product_type = detect_product_type(judul_asli)
        label = PRODUCT_TYPE_LABELS.get(product_type, "Busana")

        with st.container(border=True):
            col_h, col_regen = st.columns([5, 1])
            with col_h:
                st.markdown(
                    f"**🛍️ {judul_asli[:80]}{'...' if len(judul_asli) > 80 else ''}**"
                )
                st.caption(f"Tipe: `{product_type}` → label Pinterest: **{label}**")
            with col_regen:
                cache_key = f"titledesc_{prod_url}"
                if st.button(
                    "🔄 Ulang", key=f"regen_{prod_url}",
                    help="Generate ulang judul & deskripsi",
                    use_container_width=True,
                ):
                    if cache_key in st.session_state:
                        del st.session_state[cache_key]
                    st.rerun()

            if cache_key not in st.session_state:
                with st.spinner("Generating via Gemini..." if has_ai else "Generating..."):
                    if has_ai:
                        result = ai_generate_title_desc(
                            judul_asli, desc_asli, product_type,
                            AI_API_KEY, AI_MODEL,
                        )
                        if "error" in result:
                            st.warning(
                                f"⚠️ Gemini error: {result['error']} — fallback ke template"
                            )
                            title_fmt = format_pinterest_title(judul_asli, product_type)
                            desc_fmt = generate_description_template(
                                judul_asli, product_type, title_fmt
                            )
                            result = {"title": title_fmt, "description": desc_fmt}
                    else:
                        title_fmt = format_pinterest_title(judul_asli, product_type)
                        desc_fmt = generate_description_template(
                            judul_asli, product_type, title_fmt
                        )
                        result = {"title": title_fmt, "description": desc_fmt}

                    st.session_state[cache_key] = result

            cached = st.session_state[cache_key]
            title_out = cached.get("title", "")
            desc_out = cached.get("description", "")

            st.markdown("**📌 Judul Pinterest**")
            title_edited = st.text_area(
                label="judul_edit",
                value=title_out,
                height=75,
                max_chars=100,
                key=f"title_edit_{prod_url}",
                label_visibility="collapsed",
                help="Edit di sini kalau perlu. Max 100 karakter.",
            )
            n_title = len(title_edited)
            st.caption(
                f"{'🟢' if n_title <= 100 else '🔴'} {n_title}/100 karakter  "
                f"· Copy teks di bawah ini:"
            )
            st.code(title_edited, language=None)

            st.markdown("---")

            st.markdown("**📝 Deskripsi Pinterest**")
            desc_edited = st.text_area(
                label="desc_edit",
                value=desc_out,
                height=150,
                max_chars=500,
                key=f"desc_edit_{prod_url}",
                label_visibility="collapsed",
                help="Edit di sini kalau perlu. Max 500 karakter.",
            )
            n_desc = len(desc_edited)
            st.caption(
                f"{'🟢' if n_desc <= 500 else '🔴'} {n_desc}/500 karakter  "
                f"· Copy teks di bawah ini:"
            )
            st.code(desc_edited, language=None)

            with st.expander("🔍 Keyword SEO yang digunakan", expanded=False):
                title_kws = get_seo_title_keywords(product_type)
                desc_kws  = get_seo_desc_keywords(product_type)
                st.caption("**Title keywords:** " + "  ·  ".join(title_kws))
                st.caption("**Description keywords:** " + "  ·  ".join(desc_kws))

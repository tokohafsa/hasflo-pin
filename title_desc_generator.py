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

# Keyword SEO per tipe — dipakai di description & prompt AI
SEO_KEYWORDS = {
    "dress": [
        "floral dress", "dress bunga", "midi dress floral", "outfit kondangan",
        "dress cantik", "baju pesta floral", "fashion wanita Indonesia",
        "ootd floral", "dress motif bunga", "Pinterest fashion",
    ],
    "blouse": [
        "blouse floral", "atasan bunga", "blouse cantik", "kemeja motif bunga",
        "outfit kerja floral", "fashion wanita", "ootd blouse", "atasan wanita",
        "blouse lengan panjang", "Pinterest fashion",
    ],
    "tunik": [
        "tunik floral", "baju tunik bunga", "tunik muslim", "tunik cantik",
        "tunik wanita", "baju muslimah floral", "ootd tunik", "fashion hijab",
        "tunik motif bunga", "Pinterest outfit",
    ],
    "outer": [
        "outer floral", "cardigan bunga", "outer cantik", "jaket wanita floral",
        "outer casual", "layering outfit", "fashion wanita", "ootd outer",
        "outer motif bunga", "Pinterest style",
    ],
    "setelan": [
        "setelan floral", "baju setelan bunga", "co-ord set floral",
        "setelan wanita cantik", "matching set", "outfit setelan", "ootd setelan",
        "fashion wanita Indonesia", "setelan motif bunga", "Pinterest outfit",
    ],
    "unknown": [
        "floral fashion", "baju bunga", "fashion wanita", "outfit floral",
        "ootd floral", "busana wanita", "motif bunga", "Pinterest style",
        "fashion Indonesia", "baju cantik",
    ],
}


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
    - Kalimat 1: judul asli produk (dibersihkan)
    - Kalimat 2-4: SEO Pinterest dengan keyword per tipe
    """
    keywords = SEO_KEYWORDS.get(product_type, SEO_KEYWORDS["unknown"])

    judul_clean = re.sub(
        r'\b(terlaris|best seller|promo|diskon|gratis ongkir|cod|flash sale|murah|'
        r'import|ori|original|premium|ready|stok|koleksi terbaru)\b',
        '', judul_shopee, flags=re.IGNORECASE,
    ).strip()
    judul_clean = re.sub(r'\s+', ' ', judul_clean)

    kw1, kw2, kw3, kw4, kw5 = keywords[0], keywords[1], keywords[2], keywords[3], keywords[4]
    kw_tail = " | ".join(keywords[5:8])

    desc = (
        f"{judul_clean}. "
        f"{title_formatted} hadir dengan desain {kw1} yang anggun dan feminin, "
        f"cocok untuk berbagai kesempatan. "
        f"Temukan inspirasi {kw4} dan {kw5} terbaik untuk tampil stylish setiap hari. "
        f"{kw_tail} | fashion wanita Indonesia."
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
    Pakai SDK google-genai — sama persis dengan processor.py.
    Return: {'title': str, 'description': str} atau {'error': str}
    """
    try:
        from google import genai

        client = genai.Client(api_key=ai_api_key)

        label = PRODUCT_TYPE_LABELS.get(product_type, "Busana")
        keywords = ", ".join(SEO_KEYWORDS.get(product_type, SEO_KEYWORDS["unknown"])[:6])

        prompt = f"""Kamu adalah asisten konten Pinterest untuk akun fashion wanita motif bunga.

Judul asli produk Shopee: {judul_shopee}
Deskripsi asli: {desc_shopee or "(tidak ada)"}
Tipe produk: {product_type} ({label})
Keyword SEO Pinterest yang harus dimasukkan: {keywords}

TUGAS:
1. Buat JUDUL Pinterest (max 100 karakter):
   - Format: [Jenis produk] + motif/bunga/floral + ciri khas produk
   - Natural, tidak hard-selling, campuran Indonesia-Inggris boleh
   - Harus mencerminkan tipe produk "{label}"

2. Buat DESKRIPSI Pinterest (max 500 karakter):
   - Kalimat PERTAMA: tulis ulang judul asli produk Shopee secara natural (bukan copy-paste persis)
   - Kalimat selanjutnya: deskripsi generatif yang memaksimalkan SEO Pinterest
   - Masukkan minimal 4 keyword dari daftar di atas secara natural dalam kalimat
   - Faktual, deskriptif, tidak persuasif, tidak ada kata sales/marketing, tidak hard selling, 

Output HANYA JSON (tanpa markdown backtick):
{{"title": "...", "description": "..."}}"""

        response = client.models.generate_content(model=ai_model, contents=prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)

        # Validasi output
        if "title" not in data or "description" not in data:
            raise ValueError("Response JSON tidak lengkap")

        # Trim paksa sesuai limit Pinterest
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
    Output per produk:
      - Judul terformat (bisa diedit + copy)
      - Deskripsi SEO (bisa diedit + copy)
      - Tombol Regenerate per produk
    """
    scraped_data = st.session_state.get("scraped_data", {})
    if not scraped_data:
        return

    from processor import detect_product_type

    # Baca config — pakai Gemini sesuai config.py
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
            # Header produk
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

            # ------------------------------------------------
            # GENERATE — cache di session_state supaya tidak
            # re-generate setiap kali user berinteraksi
            # ------------------------------------------------
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

            # ------------------------------------------------
            # JUDUL
            # ------------------------------------------------
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
            # Code block = satu klik copy di Streamlit
            st.code(title_edited, language=None)

            st.markdown("---")

            # ------------------------------------------------
            # DESKRIPSI
            # ------------------------------------------------
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

            # ------------------------------------------------
            # KEYWORD INFO
            # ------------------------------------------------
            with st.expander("🔍 Keyword SEO yang digunakan", expanded=False):
                kws = SEO_KEYWORDS.get(product_type, SEO_KEYWORDS["unknown"])
                st.caption("  ·  ".join(kws))

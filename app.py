# ============================================================
# HASFLO PINTEREST - APP (PROMPT GENERATOR)
# Streamlit UI — Generate Prompt Collage untuk Image Generator
# ============================================================

import os
import re
import json
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

from image_generator import (
    build_prompt_json,
    LAYOUT_OPTIONS,
    CANVAS_OPTIONS,
)

WIB = ZoneInfo("Asia/Jakarta")

st.set_page_config(page_title="HASflo Prompt Generator", page_icon="🌸", layout="wide")

with st.sidebar:
    st.markdown("### 🌸 HASflo Prompt Generator")
    st.caption(f"WIB: {datetime.now(WIB).strftime('%d %b %Y %H:%M')}")
    st.link_button("📌 Pinterest Pin Builder", "https://id.pinterest.com/pin-builder/", use_container_width=True)
    st.link_button("🌸 HAS_flo Pinterest", "https://id.pinterest.com/HAS_flo/", use_container_width=True)
    st.link_button("🤖 ChatGPT", "https://chatgpt.com/", use_container_width=True)
    st.link_button("🛒 Shopee Affiliate Custom Link", "https://affiliate.shopee.co.id/offer/custom_link", use_container_width=True)
    st.divider()
    st.caption("File output tersimpan di folder `output/`")

BOARD_HIJAB  = "Fashion Outfit Hijab Motif Bunga"
BOARD_MODERN = "Fashion Outfit Modern Motif Bunga"

BOARD_SECTIONS_MAP = {
    BOARD_HIJAB:  ["Dress", "Blouse", "Tunik", "One Set", "Outer"],
    BOARD_MODERN: ["Dress", "Blouse", "One Set", "Outer"],
}

SECTION_MAP = {
    "dress":   "Dress",
    "blouse":  "Blouse",
    "tunik":   "Tunik",
    "outer":   "Outer",
    "setelan": "One Set",
}

PRODUCT_TYPE_KEYWORDS = {
    "dress":   ["dress", "gamis", "terusan"],
    "blouse":  ["blouse", "atasan", "kemeja"],
    "tunik":   ["tunik"],
    "outer":   ["outer", "jaket", "cardigan", "sweater"],
    "setelan": ["setelan", "one set", "co-ord"],
}

PRODUCT_TYPE_LABELS = {
    "dress":   "Dress",
    "blouse":  "Blouse",
    "tunik":   "Tunik",
    "outer":   "Outer",
    "setelan": "Setelan",
}

SEO_KEYWORDS = {
    "dress": [
        "OOTD dress motif bunga", "dress motif bunga", "inspirasi outfit dress floral",
        "dress bunga wanita", "outfit kondangan motif bunga", "dress midi floral",
        "baju pesta motif bunga", "inspirasi OOTD wanita Indonesia",
        "dress floral elegan", "fashion wanita motif bunga",
    ],
    "blouse": [
        "OOTD blouse motif bunga", "blouse motif bunga", "inspirasi outfit blouse floral",
        "atasan bunga wanita", "outfit kerja motif bunga", "blouse floral casual",
        "kemeja motif bunga wanita", "inspirasi OOTD atasan bunga",
        "fashion atasan motif bunga", "blouse wanita Indonesia",
    ],
    "tunik": [
        "OOTD tunik motif bunga", "tunik motif bunga", "inspirasi outfit tunik floral",
        "tunik bunga muslimah", "baju tunik motif bunga", "tunik floral hijab",
        "outfit tunik wanita Indonesia", "inspirasi OOTD tunik bunga",
        "fashion muslimah motif bunga", "tunik casual motif bunga",
    ],
    "outer": [
        "OOTD outer motif bunga", "outer motif bunga", "inspirasi outfit outer floral",
        "cardigan bunga wanita", "jaket motif bunga wanita", "layering outfit motif bunga",
        "outer floral casual", "inspirasi OOTD outer bunga",
        "fashion outer motif bunga", "cardigan floral wanita Indonesia",
    ],
    "setelan": [
        "OOTD setelan motif bunga", "setelan motif bunga", "inspirasi outfit setelan floral",
        "baju setelan bunga wanita", "co-ord set motif bunga", "matching set motif bunga",
        "setelan floral wanita", "inspirasi OOTD setelan bunga",
        "fashion setelan motif bunga", "setelan casual motif bunga",
    ],
}


def detect_product_type(judul: str) -> str:
    judul_lower = judul.lower()
    for tipe, keywords in PRODUCT_TYPE_KEYWORDS.items():
        if any(kw in judul_lower for kw in keywords):
            return tipe
    return "dress"


def get_board_from_hijab(is_hijab: bool, product_type: str) -> str:
    if product_type == "tunik":
        return BOARD_HIJAB
    return BOARD_HIJAB if is_hijab else BOARD_MODERN


def scan_model_files(is_hijab: bool, models_dir: str = None) -> list:
    if models_dir is None:
        models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "models")
    if not os.path.isdir(models_dir):
        return []
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    files = sorted([f for f in os.listdir(models_dir) if os.path.splitext(f)[1].lower() in exts])
    result = []
    for f in files:
        stem = os.path.splitext(f)[0]
        has_hijab_tag = "hijab" in stem.lower()
        if is_hijab and has_hijab_tag:
            result.append(stem)
        elif not is_hijab and not has_hijab_tag:
            result.append(stem)
    return result


CLEAR_KEYS = [
    "image_urls", "url_slots", "judul_input_field",
    "shopee_affiliate_link", "generated_title", "generated_desc",
    "title_desc_done", "_product_type_val", "_judul_checked",
    "last_prompt_json", "use_model_ref", "selected_model_name",
    "canvas_size_label", "selected_board", "selected_section", "is_hijab",
    "title_edit", "desc_edit",
]

defaults = {
    "image_urls": [],
    "url_slots": [""],
    "judul_input_field": "",
    "shopee_affiliate_link": "",
    "generated_title": "",
    "generated_desc": "",
    "title_desc_done": False,
    "_product_type_val": "dress",
    "_judul_checked": False,
    "selected_layout_name": LAYOUT_OPTIONS[0]["name"] if LAYOUT_OPTIONS else "",
    "last_prompt_json": None,
    "use_model_ref": False,
    "selected_model_name": None,
    "is_hijab": True,
    "selected_board": BOARD_HIJAB,
    "selected_section": "Dress",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Default values untuk variabel yang dipakai downstream
# Akan di-override jika _judul_checked = True dan user mengisi Step 3/4
selected_model_name = None
subject_desc = "female, warm Indonesian face, wearing hijab, 25 years old"

st.title("🌸 HASflo Prompt Generator")
st.caption("Generate prompt collage siap pakai untuk Midjourney, Gemini, atau ChatGPT.")
st.divider()

# ============================================================
# STEP 1A — LINK AFFILIATE SHOPEE
# ============================================================

st.subheader("Step 1A — 🔗 Link Affiliate Shopee *(opsional)*")
st.caption("Akan disertakan di deskripsi.txt dalam folder `ready_pin/` di Dropbox untuk agent Pinterest.")

shopee_affiliate_link = st.text_input(
    "Link affiliate Shopee:",
    placeholder="https://s.shopee.co.id/AAFmsXfSnq.",
    key="shopee_affiliate_link",
)
if shopee_affiliate_link.strip():
    shopee_affiliate_link = shopee_affiliate_link.strip().rstrip(".")
    st.markdown(f'✅ Link affiliate: <a href="{shopee_affiliate_link}" target="_blank">{shopee_affiliate_link}</a>', unsafe_allow_html=True)

st.divider()

# ============================================================
# STEP 1 — INPUT URL GAMBAR
# ============================================================

st.header("Step 1 — Input URL Gambar Produk")

if st.button("🗑️ Clear Semua — Input Baru", key="btn_clear_all"):
    # Hapus semua url_slot_N widget keys dulu sebelum clear url_slots
    _n_slots = len(st.session_state.get("url_slots", [""]))
    for _i in range(_n_slots):
        if f"url_slot_{_i}" in st.session_state:
            del st.session_state[f"url_slot_{_i}"]
    for k in CLEAR_KEYS:
        if k in st.session_state:
            del st.session_state[k]
    for layout in LAYOUT_OPTIONS:
        for suffix in ["n_photo_slots_", "highlight_"]:
            key = f"{suffix}{layout['name']}"
            if key in st.session_state:
                del st.session_state[key]
    st.session_state["url_slots"] = [""]
    st.rerun()

st.caption("Isi satu URL per field. Field baru muncul otomatis setelah field sebelumnya diisi.")

if "url_slots" not in st.session_state or not st.session_state["url_slots"]:
    st.session_state["url_slots"] = [""]

for i in range(len(st.session_state["url_slots"])):
    _col_url, _col_clr = st.columns([10, 1])
    with _col_url:
        st.session_state["url_slots"][i] = st.text_input(
            f"URL gambar {i + 1}:",
            value=st.session_state["url_slots"][i],
            key=f"url_slot_{i}",
            placeholder="https://down-id.img.susercontent.com/file/xxx.webp",
        )
    with _col_clr:
        st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
        if st.button("✕", key=f"clr_slot_{i}", help="Hapus URL ini"):
            st.session_state["url_slots"].pop(i)
            if f"url_slot_{i}" in st.session_state:
                del st.session_state[f"url_slot_{i}"]
            if not st.session_state["url_slots"]:
                st.session_state["url_slots"] = [""]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

if st.session_state["url_slots"][-1].strip():
    st.session_state["url_slots"].append("")
    st.rerun()

urls_parsed = [u.strip() for u in st.session_state["url_slots"] if u.strip()]
cleaned_urls = [re.sub(r"@resize_[^.]+", "", u) for u in urls_parsed]
st.session_state["image_urls"] = cleaned_urls

if cleaned_urls:
    st.success(f"✅ {len(cleaned_urls)} URL — akan jadi {len(cleaned_urls)} referensi outfit di prompt.")
    preview_cols = st.columns(min(len(cleaned_urls), 8))
    for i, url in enumerate(cleaned_urls):
        with preview_cols[i % 8]:
            st.image(url, width=80)
            st.caption(f"Ref {i + 1}")
else:
    st.session_state["image_urls"] = []

import random as _random
canvas_key_options = list(CANVAS_OPTIONS.keys())
canvas_labels = [CANVAS_OPTIONS[k]["label"] for k in canvas_key_options]

if "canvas_size_label" not in st.session_state:
    st.session_state["canvas_size_label"] = _random.choice(canvas_labels)

selected_canvas_label = st.selectbox("Ukuran canvas:", options=canvas_labels, key="canvas_size_label")
selected_canvas_key = canvas_key_options[canvas_labels.index(selected_canvas_label)]

st.divider()

# ============================================================
# STEP 2 — JUDUL PRODUK + CEK
# ============================================================

st.header("Step 2 — Judul Produk & Generate Title Pinterest")
st.caption(
    "Isi judul produk dari Shopee, klik **Cek Judul** untuk deteksi tipe outfit, "
    "lalu pilih hijab/non-hijab untuk menentukan board."
)

judul_input = st.text_input(
    "Judul produk (dari Shopee):",
    placeholder="contoh: Dress Wanita Motif Bunga Premium Rayon Midi Terbaru",
    key="judul_input_field",
)

can_cek = bool(judul_input.strip())

if st.button("🔍 Cek Judul", disabled=not can_cek, key="btn_cek_judul"):
    detected = detect_product_type(judul_input)
    st.session_state["_product_type_val"] = detected
    st.session_state["_judul_checked"] = True
    st.session_state["title_desc_done"] = False

# ============================================================
# STEP 2B — SECTION + HIJAB + BOARD + GENERATE
# (muncul setelah Cek Judul)
# ============================================================

if st.session_state.get("_judul_checked"):

    st.markdown("---")
    st.subheader("Step 2B — Board & Section")

    _pt_options = ["dress", "blouse", "tunik", "outer", "setelan"]
    _pt_default = st.session_state.get("_product_type_val", "dress")
    _pt_index = _pt_options.index(_pt_default) if _pt_default in _pt_options else 0

    st.info(f"✅ Tipe outfit terdeteksi: **{PRODUCT_TYPE_LABELS.get(_pt_default, _pt_default)}**")

    col_pt, col_hijab = st.columns([1, 1])

    with col_pt:
        product_type = st.selectbox(
            "Konfirmasi tipe outfit (Section):",
            options=_pt_options,
            index=_pt_index,
            key="outfit_type_confirmed",
            help="Auto-detect dari judul. Koreksi manual kalau perlu.",
        )
        st.session_state["_product_type_val"] = product_type

    with col_hijab:
        _tunik_lock = product_type == "tunik"
        if _tunik_lock:
            st.selectbox(
                "Konten:",
                options=["Hijab"],
                index=0,
                key="hijab_selector_locked",
                disabled=True,
                help="Tunik selalu masuk board Hijab.",
            )
            is_hijab = True
        else:
            _hijab_default_idx = 0 if st.session_state.get("is_hijab", True) else 1
            _hijab_sel = st.selectbox(
                "Konten:",
                options=["Hijab", "Non-Hijab"],
                index=_hijab_default_idx,
                key="hijab_selector",
                help="Menentukan board Pinterest dan filter model reference.",
            )
            is_hijab = (_hijab_sel == "Hijab")

        st.session_state["is_hijab"] = is_hijab

    selected_board   = get_board_from_hijab(is_hijab, product_type)
    selected_section = SECTION_MAP.get(product_type, "Dress")
    st.session_state["selected_board"]   = selected_board
    st.session_state["selected_section"] = selected_section
    st.caption(f"📌 Pin akan masuk: **{selected_board}** › **{selected_section}**")

    st.markdown("---")

    if st.button("✨ Generate Judul & Deskripsi", key="btn_gen_titledesc", type="primary"):
        with st.spinner("Generating via Gemini..."):
            try:
                from _credentials import AI_API_KEY, AI_MODEL
                from google import genai

                client = genai.Client(api_key=AI_API_KEY)
                label    = PRODUCT_TYPE_LABELS.get(product_type, "Busana")
                keywords = ", ".join(SEO_KEYWORDS.get(product_type, [])[:6])

                prompt_ai = f"""Kamu adalah asisten konten Pinterest untuk akun fashion wanita motif bunga Indonesia.

Judul asli produk Shopee: {judul_input}
Tipe produk: {product_type} ({label})
Keyword SEO Pinterest yang tersedia: {keywords}

TUGAS 1 — JUDUL Pinterest (max 100 karakter):
- Format wajib: [Tipe Outfit] + "Motif Bunga" + ciri khas produk (bahan/potongan/panjang/warna jika ada di judul)
- Contoh: "Dress Motif Bunga Midi Rayon Lengan Panjang", "Blouse Motif Bunga Oversized Casual"
- Kata "OOTD" TIDAK perlu masuk judul — simpan untuk deskripsi
- Natural, tidak hard-selling, tidak mengandung kata promo/diskon/murah

TUGAS 2 — DESKRIPSI Pinterest (max 500 karakter):
- Kalimat 1 WAJIB: salin judul asli produk Shopee APA ADANYA sebagai kalimat pertama — VERBATIM
- Kalimat 2 WAJIB: harus mengandung kata "OOTD" dan "motif bunga"
- Kalimat 3-4: masukkan minimal 3 keyword lain dari daftar secara natural
- Seluruh deskripsi: Bahasa Indonesia, faktual, deskriptif, TIDAK persuasif
- DILARANG: "dapatkan sekarang", "segera beli", "klik link", "harga spesial", "promo"

Output HANYA JSON (tanpa markdown backtick):
{{"title": "...", "description": "..."}}"""

                response = client.models.generate_content(model=AI_MODEL, contents=prompt_ai)
                text = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(text)

                st.session_state["generated_title"] = data.get("title", "")[:100]
                st.session_state["generated_desc"]  = data.get("description", "")[:500]
                st.session_state["title_desc_done"]  = True

            except Exception as e:
                st.error(f"❌ Gemini error: {e}")
                st.session_state["title_desc_done"] = False

    if st.session_state.get("title_desc_done"):
        st.markdown("---")
        col_t, col_d = st.columns([1, 1])

        with col_t:
            st.markdown("**📌 Judul Pinterest** (edit kalau perlu):")
            title_edited = st.text_area(
                label="title_edit_area",
                value=st.session_state["generated_title"],
                height=80, max_chars=100,
                key="title_edit", label_visibility="collapsed",
            )
            st.caption(f"{'🟢' if len(title_edited) <= 100 else '🔴'} {len(title_edited)}/100 karakter")
            st.code(title_edited, language=None)

        with col_d:
            st.markdown("**📝 Deskripsi Pinterest** (edit kalau perlu):")
            desc_edited = st.text_area(
                label="desc_edit_area",
                value=st.session_state["generated_desc"],
                height=150, max_chars=500,
                key="desc_edit", label_visibility="collapsed",
            )
            st.caption(f"{'🟢' if len(desc_edited) <= 500 else '🔴'} {len(desc_edited)}/500 karakter")
            st.code(desc_edited, language=None)

st.divider()

# ============================================================
# STEP 3 — MODEL REFERENCE
# Hanya muncul setelah _judul_checked = True
# → is_hijab sudah pasti ter-set dari Step 2B
# ============================================================

st.header("Step 3 — Model Reference *(opsional)*")

if not st.session_state.get("_judul_checked"):
    st.info("⬆️ Isi judul produk di Step 2 dan klik **Cek Judul** untuk melanjutkan.")
else:
    st.caption(
        "Aktifkan untuk menyertakan gambar wajah/model sebagai referensi visual. "
        "File model difilter otomatis berdasarkan pilihan Hijab/Non-Hijab di Step 2B."
    )

    _is_hijab_now = st.session_state.get("is_hijab", True)
    MODEL_LIST = scan_model_files(_is_hijab_now)

    use_model_ref = st.toggle(
        "Gunakan Model Reference",
        value=st.session_state.get("use_model_ref", False),
        key="use_model_ref",
        help="Gambar model dari assets/models/ akan diupload pertama ke GPT.",
    )

    if use_model_ref:
        if not MODEL_LIST:
            _tag = "hijab" if _is_hijab_now else "non-hijab"
            _models_dir_dbg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "models")
            st.warning(
                f"⚠️ Tidak ada file model {_tag} ditemukan di `assets/models/`. "
                f"{'Tambahkan file dengan kata \"hijab\" di nama file.' if _is_hijab_now else 'Tambahkan file tanpa kata \"hijab\" di nama file.'}"
            )
            st.caption(f"🔍 Debug path: `{_models_dir_dbg}` — exists: `{os.path.isdir(_models_dir_dbg)}`")
            if os.path.isdir(_models_dir_dbg):
                _all_files = os.listdir(_models_dir_dbg)
                st.caption(f"Files ditemukan: `{_all_files}`")
        else:
            selected_model_name = st.selectbox(
                "Pilih model:",
                options=MODEL_LIST,
                key="selected_model_name",
            )
            model_exts = [".png", ".jpg", ".jpeg", ".webp"]
            model_preview_path = None
            if selected_model_name:
                _models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "models")
                for ext in model_exts:
                    candidate = os.path.join(_models_dir, selected_model_name + ext)
                    if os.path.isfile(candidate):
                        model_preview_path = candidate
                        break
            if model_preview_path:
                col_mp, col_mi = st.columns([1, 3])
                with col_mp:
                    st.image(model_preview_path, width=100)
                with col_mi:
                    st.success(f"✅ Model: **{selected_model_name}**")
                    st.caption("Gambar ini akan diupload ke GPT sebagai gambar pertama.")

st.divider()

# ============================================================
# STEP 4 — SUBJECT
# Hanya muncul setelah _judul_checked = True
# → is_hijab sudah pasti ter-set, ras terkunci kalau hijab
# ============================================================

st.header("Step 4 — Deskripsi Subject")

if not st.session_state.get("_judul_checked"):
    st.info("⬆️ Isi judul produk di Step 2 dan klik **Cek Judul** untuk melanjutkan.")
else:
    _age_options = ["18 years old", "25 years old", "33 years old"]

    # ── Deteksi nationality dari nama model (jika toggle model ON) ──
    _use_model_now  = st.session_state.get("use_model_ref", False)
    _model_name_now = st.session_state.get("selected_model_name", "") or ""
    _model_lower    = _model_name_now.lower()
    _is_hijab_subject = st.session_state.get("is_hijab", True)

    # Deteksi tipe model dari nama file
    _model_is_indo  = _use_model_now and (
        _model_lower.startswith("indo") or "indonesian" in _model_lower
    )
    _model_is_asian = _use_model_now and (
        _model_lower.startswith("asian") or "asian" in _model_lower
    )

    # Tentukan nationality options & lock state
    if _use_model_now and _model_is_indo:
        # Model Indo/IndoHijab → terkunci Indonesian
        _nationality_options  = ["Indonesian"]
        _nationality_disabled = True
        _nationality_help     = "Terkunci Indonesian sesuai model reference yang dipilih."
    elif _use_model_now and _model_is_asian:
        # Model Asian → Korean, Chinese, Japanese (tanpa Indonesian)
        _nationality_options  = ["Korean", "Chinese", "Japanese"]
        _nationality_disabled = False
        _nationality_help     = "Nationality disesuaikan dengan model Asian yang dipilih."
    elif _is_hijab_subject:
        # Hijab tanpa model → terkunci Indonesian
        _nationality_options  = ["Indonesian"]
        _nationality_disabled = True
        _nationality_help     = "Terkunci Indonesian karena konten Hijab."
    else:
        # Default — bebas pilih
        _nationality_options  = ["Indonesian", "Korean", "Chinese", "Japanese"]
        _nationality_disabled = False
        _nationality_help     = ""

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        subject_age = st.selectbox("Usia:", options=_age_options, key="subject_age")

    with col_s2:
        subject_nationality = st.selectbox(
            "Nationality:",
            options=_nationality_options,
            key="subject_nationality",
            disabled=_nationality_disabled,
            help=_nationality_help,
        )

    subject_custom = st.text_input(
        "Atau tulis sendiri (opsional, menggantikan pilihan di atas jika diisi):",
        placeholder="contoh: female model, East African face, 30 years old, natural hair",
        key="subject_custom",
    )

    if subject_custom.strip():
        custom = subject_custom.strip()
        subject_desc = f"female, {custom}" if "female" not in custom.lower() else custom
    else:
        nationality_map = {
            "Indonesian": "warm Indonesian face",
            "Korean":     "Korean face",
            "Chinese":    "Chinese face",
            "Japanese":   "Japanese face",
        }
        nat_str       = nationality_map.get(subject_nationality, "warm Indonesian face")
        hijab_str     = ", wearing hijab" if _is_hijab_subject else ", no hijab"
        subject_desc  = f"female, {nat_str}{hijab_str}, {subject_age}"

    st.caption(f"Subject: `{subject_desc}`")

st.divider()

# ============================================================
# STEP 5 — PILIH LAYOUT
# ============================================================

st.header("Step 5 — Pilih Layout Collage")
st.caption("Pilih satu layout referensi collage.")

if not LAYOUT_OPTIONS:
    st.warning("⚠️ Tidak ada layout ditemukan di folder `assets/`.")
else:
    if st.session_state.get("selected_layout_name") not in [l["name"] for l in LAYOUT_OPTIONS]:
        st.session_state["selected_layout_name"] = LAYOUT_OPTIONS[0]["name"]

    for row_start in range(0, len(LAYOUT_OPTIONS), 2):
        row_layouts = LAYOUT_OPTIONS[row_start: row_start + 2]
        row_cols = st.columns(2)

        for col_idx, layout in enumerate(row_layouts):
            with row_cols[col_idx]:
                is_selected = st.session_state["selected_layout_name"] == layout["name"]

                with st.container(border=is_selected):
                    inner_col_img, inner_col_info = st.columns([1, 2])

                    with inner_col_img:
                        st.image(layout["preview_path"], use_container_width=True)

                    with inner_col_info:
                        st.markdown(f"**{layout['name'].upper()}**")
                        tags_str = "  ".join(f"`{t}`" for t in layout.get("tags", []))
                        if tags_str:
                            st.markdown(tags_str)
                        desc_short = layout.get("description", "")
                        if len(desc_short) > 120:
                            desc_short = desc_short[:117] + "..."
                        st.caption(desc_short)

                        slot_options = [3, 4, 5, 6, 7]
                        default_slot = layout.get("n_photo_slots", 4)
                        default_idx  = slot_options.index(default_slot) if default_slot in slot_options else 1
                        st.selectbox(
                            "Jumlah photo slot:",
                            options=slot_options,
                            index=default_idx,
                            key=f"n_photo_slots_{layout['name']}",
                        )
                        st.radio(
                            "Hero shot:",
                            options=["No Highlight", "Full Shot", "Medium Shot"],
                            index=1,
                            key=f"highlight_{layout['name']}",
                            horizontal=True,
                        )

                        if st.button(
                            "✅ Dipilih" if is_selected else "Pilih Layout",
                            key=f"layout_btn_{layout['name']}",
                            type="primary" if is_selected else "secondary",
                            use_container_width=True,
                        ):
                            st.session_state["selected_layout_name"] = layout["name"]
                            st.rerun()

    selected_layout = next(
        (l for l in LAYOUT_OPTIONS if l["name"] == st.session_state["selected_layout_name"]),
        LAYOUT_OPTIONS[0],
    )
    n_photo_slots  = st.session_state.get(f"n_photo_slots_{selected_layout['name']}", 4)
    highlight_mode = st.session_state.get(f"highlight_{selected_layout['name']}", "Full Shot")

    st.info(
        f"Layout aktif: **{selected_layout['name']}**  ·  "
        f"Canvas: **{CANVAS_OPTIONS[selected_canvas_key]['label']}**  ·  "
        f"Photo slots: **{n_photo_slots}**  ·  "
        f"Hero shot: **{highlight_mode}**"
    )

st.divider()

# ============================================================
# STEP 6 — GENERATE PROMPT
# ============================================================

st.header("Step 6 — Generate Prompt")

n_ref_images = len(st.session_state.get("image_urls", []))
can_generate  = n_ref_images >= 1 and bool(LAYOUT_OPTIONS)

if not can_generate:
    st.warning("⚠️ Masukkan minimal 1 URL gambar di Step 1 untuk bisa generate prompt.")

if st.button("✨ Generate Prompt", type="primary", disabled=not can_generate, key="gen_btn_main"):
    with st.spinner("Generating prompt..."):
        prompt_dict = build_prompt_json(
            outfit_type=st.session_state.get("_product_type_val", "dress"),
            subject_description=subject_desc,
            layout_name=selected_layout["name"],
            layout_description=selected_layout["description"],
            n_product_images=n_ref_images,
            n_photo_slots=n_photo_slots,
            swipe_cta=selected_layout.get("raw", {}).get("swipe_cta"),
            canvas_size=selected_canvas_key,
            highlight=highlight_mode,
            model_name=(selected_model_name if st.session_state.get("use_model_ref") else None),
        )
        st.session_state["last_prompt_json"] = prompt_dict

# ============================================================
# STEP 7 — HASIL PROMPT
# ============================================================

if st.session_state.get("last_prompt_json"):
    prompt_dict = st.session_state["last_prompt_json"]

    st.success("✅ Prompt siap!")
    st.divider()
    st.subheader("📋 Hasil Prompt")

    has_title = (
        st.session_state.get("title_desc_done")
        and st.session_state.get("title_edit", "").strip()
    )
    if has_title:
        st.markdown("**📌 Judul Pinterest:**")
        st.code(st.session_state.get("title_edit", ""), language=None)
        st.markdown("**📝 Deskripsi Pinterest:**")
        st.code(st.session_state.get("desc_edit", ""), language=None)
        st.markdown("---")

    st.markdown("**🎨 Prompt Collage** (paste ke Midjourney / Gemini / ChatGPT):")
    with st.expander("📄 Lihat & Copy Prompt", expanded=False):
        st.code(prompt_dict["prompt"], language=None, wrap_lines=True)

    image_urls     = st.session_state.get("image_urls", [])
    layout_preview = selected_layout.get("preview_path", "")

    sum_cols = st.columns(len(image_urls) + 1) if image_urls else st.columns(1)
    for i, url in enumerate(image_urls):
        with sum_cols[i]:
            st.image(url, use_container_width=True)
            st.caption(f"Ref {i + 1}")
    with sum_cols[-1]:
        if layout_preview and os.path.isfile(layout_preview):
            st.image(layout_preview, use_container_width=True)
        st.caption(f"Layout: {selected_layout['name']}")

    st.markdown("**📂 Urutan upload gambar ke platform:**")
    for key, val in prompt_dict["placeholders"].items():
        st.caption(f"• {val}")
    st.caption(f"💡 {prompt_dict['settings']['platform_notes']}")

    st.markdown("**⚙️ Detail settings prompt:**")
    s = prompt_dict["settings"]
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.caption(f"Outfit: `{s['outfit_type']}`")
        st.caption(f"Layout: `{s['layout_selected']}`")
        st.caption(f"Photo slots: `{s['n_photo_slots']}`")
    with col_s2:
        st.caption(f"Referensi gambar: `{s['n_product_images']}`")
        st.caption(f"Total upload: `{s['total_images_to_upload']}`")
        st.caption(f"Canvas: `{s['aspect_ratio_recommended']}`")

    st.markdown("---")

    # ============================================================
    # STEP 7 — UPLOAD BAHAN PROMPT KE DROPBOX
    # ============================================================

    st.header("Step 7 — Upload Bahan Prompt ke Dropbox")
    st.caption(
        "Fetch gambar outfit dari Shopee, build folder `bahan_prompt/`, "
        "lalu upload ke Dropbox. Setelah ini buka Dropbox → upload ke GPT → dapat hasil gambar."
    )

    if st.button("☁️ Upload Bahan Prompt ke Dropbox", key="btn_upload_bahan", type="primary", use_container_width=True):
        import requests as _requests
        import os as _os
        from dropbox_client import upload_bytes as _dbx_upload_bytes, _get_access_token as _dbx_token

        try:
            from _credentials import (
                DROPBOX_APP_KEY, DROPBOX_APP_SECRET,
                DROPBOX_REFRESH_TOKEN, DROPBOX_FOLDER,
            )
        except ImportError as e:
            st.error(f"❌ Config Dropbox tidak ditemukan: {e}")
            st.stop()

        image_urls   = st.session_state.get("image_urls", [])
        layout_prev  = selected_layout.get("preview_path", "")

        _canvas_ratio = CANVAS_OPTIONS.get(selected_canvas_key, {}).get("ratio", "")
        _ratio_prefix = f"[{_canvas_ratio.replace(':', 'x')}]" if _canvas_ratio else ""
        judul_asli    = st.session_state.get("judul_input_field", "").strip()
        _safe         = re.sub(r'[\\/*?:"<>|]', "", judul_asli).strip().replace(" ", "_")[:20] if judul_asli else "hasflo_pin"
        _datestamp    = datetime.now().strftime("%Y%m%d")
        folder_name   = f"{_safe}_{_ratio_prefix}_{_datestamp}"

        _use_model    = st.session_state.get("use_model_ref", False)
        _model_name   = st.session_state.get("selected_model_name") if _use_model else None
        _outfit_start = 2 if (_use_model and _model_name) else 1

        dbx_bp = f"{DROPBOX_FOLDER.rstrip('/')}/{folder_name}/bahan_prompt"
        errors, uploads = [], []

        _prog = st.progress(0, text="Menghubungkan ke Dropbox...")

        try:
            _token = _dbx_token(DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN)
        except Exception as e:
            st.error(f"❌ Token Dropbox gagal: {e}")
            st.stop()

        outfit_files = {}
        total_steps  = len(image_urls) + 3
        step         = 0

        for idx, url in enumerate(image_urls, start=1):
            step += 1
            _prog.progress(int(step / total_steps * 100), text=f"Fetch outfit ref {idx}...")
            try:
                resp = _requests.get(url, timeout=15)
                resp.raise_for_status()
                ct  = resp.headers.get("Content-Type", "image/jpeg")
                ext = ct.split("/")[-1].split(";")[0].strip()
                if ext not in ("jpg", "jpeg", "png", "webp"):
                    ext = "jpg"
                outfit_files[idx] = (ext, resp.content)
                gpt_idx = idx + (_outfit_start - 1)
                _dbx_upload_bytes(resp.content, f"{dbx_bp}/image{gpt_idx}.{ext}", _token)
                uploads.append(f"image{gpt_idx}.{ext}")
            except Exception as e:
                errors.append(f"image{idx}: {e}")

        step += 1
        if _use_model and _model_name:
            _prog.progress(int(step / total_steps * 100), text="Upload model reference...")
            _model_exts = [".png", ".jpg", ".jpeg", ".webp"]
            _model_path = None
            _models_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets", "models")
            for _ext in _model_exts:
                _c = _os.path.join(_models_dir, _model_name + _ext)
                if _os.path.isfile(_c):
                    _model_path = _c
                    break
            if _model_path:
                _mext = _os.path.splitext(_model_path)[-1].lstrip(".") or "jpg"
                with open(_model_path, "rb") as _mf:
                    _dbx_upload_bytes(_mf.read(), f"{dbx_bp}/_model_ref.{_mext}", _token)
                uploads.append(f"_model_ref.{_mext}")
            else:
                _all_files = _os.listdir(_models_dir) if _os.path.isdir(_models_dir) else []
                errors.append(
                    f"File model '{_model_name}' tidak ditemukan. "
                    f"Path: {_models_dir} | "
                    f"Files: {_all_files}"
                )

        step += 1
        _prog.progress(int(step / total_steps * 100), text="Upload layout...")
        if layout_prev and _os.path.isfile(layout_prev):
            _lext = _os.path.splitext(layout_prev)[-1].lstrip(".") or "jpg"
            with open(layout_prev, "rb") as lf:
                _dbx_upload_bytes(lf.read(), f"{dbx_bp}/layout.{_lext}", _token)
            uploads.append(f"layout.{_lext}")
        else:
            errors.append(f"Layout preview tidak ditemukan: {layout_prev}")

        step += 1
        _prog.progress(int(step / total_steps * 100), text="Upload prompt.txt...")
        try:
            _dbx_upload_bytes(prompt_dict["prompt"].encode("utf-8"), f"{dbx_bp}/prompt.txt", _token)
            uploads.append("prompt.txt")
        except Exception as e:
            errors.append(f"prompt.txt: {e}")

        _prog.empty()

        st.session_state["_folder_name"]    = folder_name
        st.session_state["_outfit_files"]   = outfit_files
        st.session_state["_bahan_uploaded"] = True

        for err in errors:
            st.warning(f"⚠️ {err}")

        if uploads:
            st.success(
                f"✅ `bahan_prompt/` terupload ke Dropbox! ({len(uploads)} file) → "
                f"`{DROPBOX_FOLDER.rstrip('/')}/{folder_name}/bahan_prompt/`"
            )
            st.link_button(
                "🤖 Buka ChatGPT — siap upload file",
                "https://chatgpt.com/",
                use_container_width=True,
                type="primary",
            )
            st.caption("Buka Dropbox → ambil file dari `bahan_prompt/` → upload ke ChatGPT → paste prompt.txt → balik ke sini untuk Step 8.")

# ============================================================
# STEP 8 — UPLOAD HASIL GPT → READY PIN
# ============================================================

st.divider()
st.header("Step 8 — Upload Hasil GPT & Kirim Ready Pin")

_bahan_done = st.session_state.get("_bahan_uploaded", False)

if not _bahan_done:
    st.info("⬆️ Selesaikan Step 7 dulu (upload bahan prompt ke Dropbox).")
else:
    _folder_name  = st.session_state.get("_folder_name", "")
    _outfit_files = st.session_state.get("_outfit_files", {})

    st.caption(
        f"Folder aktif: `{_folder_name}` — "
        "drag & drop hasil GPT di bawah, lalu upload `ready_pin/` ke Dropbox."
    )

    st.markdown("**🖼️ Hasil GPT (Slide 1)**")
    gpt_file = st.file_uploader(
        "Drag & drop gambar hasil GPT:",
        type=["png", "jpg", "jpeg", "webp"],
        key="gpt_result_file",
        label_visibility="collapsed",
    )

    if gpt_file:
        gpt_bytes = gpt_file.read()
        gpt_ext   = gpt_file.name.rsplit(".", 1)[-1].lower() if "." in gpt_file.name else "png"

        st.markdown("**📋 Preview urutan slide carousel:**")
        all_slides = [("Slide 1 — Hasil GPT", gpt_bytes, gpt_ext)]
        for idx, (ext, data) in sorted(_outfit_files.items()):
            all_slides.append((f"Slide {idx + 1} — Outfit Ref {idx}", data, ext))

        preview_cols = st.columns(min(len(all_slides), 5))
        for i, (label, data, ext) in enumerate(all_slides):
            with preview_cols[i % 5]:
                st.image(data, use_container_width=True)
                st.caption(label)

        st.markdown("---")

        if st.button("☁️ Upload Ready Pin ke Dropbox", key="btn_upload_ready", type="primary", use_container_width=True):
            from dropbox_client import upload_bytes as _dbx_upload_bytes, _get_access_token as _dbx_token

            try:
                from _credentials import (
                    DROPBOX_APP_KEY, DROPBOX_APP_SECRET,
                    DROPBOX_REFRESH_TOKEN, DROPBOX_FOLDER,
                )
            except ImportError as e:
                st.error(f"❌ Config Dropbox tidak ditemukan: {e}")
                st.stop()

            title_pin      = st.session_state.get("title_edit", "").strip()
            desc_pin       = st.session_state.get("desc_edit", "").strip()
            link_affiliate = st.session_state.get("shopee_affiliate_link", "").strip().rstrip(".")
            _board         = st.session_state.get("selected_board", BOARD_HIJAB)
            _section       = st.session_state.get("selected_section", "Dress")
            judul_asli     = st.session_state.get("judul_input_field", "").strip()

            dbx_rp     = f"{DROPBOX_FOLDER.rstrip('/')}/{_folder_name}/ready_pin"
            errors_rp  = []
            uploads_rp = []

            _prog2 = st.progress(0, text="Menghubungkan ke Dropbox...")

            try:
                _token = _dbx_token(DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN)
            except Exception as e:
                st.error(f"❌ Token Dropbox gagal: {e}")
                st.stop()

            total_rp = len(_outfit_files) + 2
            step_rp  = 0

            step_rp += 1
            _prog2.progress(int(step_rp / total_rp * 100), text="Upload Slide 1 (hasil GPT)...")
            try:
                _dbx_upload_bytes(gpt_bytes, f"{dbx_rp}/slides/slide1.{gpt_ext}", _token)
                uploads_rp.append(f"slides/slide1.{gpt_ext}")
            except Exception as e:
                errors_rp.append(f"slide1: {e}")

            for idx, (ext, data) in sorted(_outfit_files.items()):
                step_rp += 1
                _prog2.progress(int(step_rp / total_rp * 100), text=f"Upload image{idx}.{ext}...")
                try:
                    _dbx_upload_bytes(data, f"{dbx_rp}/image{idx}.{ext}", _token)
                    uploads_rp.append(f"image{idx}.{ext}")
                except Exception as e:
                    errors_rp.append(f"image{idx}: {e}")

            step_rp += 1
            _prog2.progress(int(step_rp / total_rp * 100), text="Upload deskripsi.txt...")
            desc_lines = [
                f"{_board}/{_section}",
                title_pin or judul_asli,
                desc_pin,
                link_affiliate,
            ]
            try:
                _dbx_upload_bytes(
                    "\n".join(desc_lines).encode("utf-8"),
                    f"{dbx_rp}/deskripsi.txt",
                    _token,
                )
                uploads_rp.append("deskripsi.txt")
            except Exception as e:
                errors_rp.append(f"deskripsi.txt: {e}")

            _prog2.empty()

            for err in errors_rp:
                st.warning(f"⚠️ {err}")

            if uploads_rp:
                # ── Rename folder parent: tambah prefix READY_ ──
                _old_parent = f"{DROPBOX_FOLDER.rstrip('/')}/{_folder_name}"
                _new_folder_name = f"READY_{_folder_name}"
                _new_parent = f"{DROPBOX_FOLDER.rstrip('/')}/{_new_folder_name}"
                try:
                    from dropbox_client import rename_folder as _dbx_rename
                    _dbx_rename(_old_parent, _new_parent, _token)
                    st.session_state["_folder_name"] = _new_folder_name
                    st.success(
                        f"✅ `ready_pin/` terupload! ({len(uploads_rp)} file) → "
                        f"`{_new_parent}/ready_pin`"
                    )
                    st.info(f"📁 Folder direname → `{_new_folder_name}`")
                except Exception as _e:
                    st.success(
                        f"✅ `ready_pin/` terupload! ({len(uploads_rp)} file) → "
                        f"`{dbx_rp}`"
                    )
                    st.warning(f"⚠️ Rename folder gagal: {_e}")
                st.caption("Agent Pinterest siap memproses folder ini.")

st.divider()
if st.button("🌸 Input Baru — Produk Berikutnya", type="primary", use_container_width=True, key="btn_input_baru"):
    _n_slots = len(st.session_state.get("url_slots", [""]))
    for _i in range(_n_slots):
        if f"url_slot_{_i}" in st.session_state:
            del st.session_state[f"url_slot_{_i}"]
    for k in CLEAR_KEYS:
        if k in st.session_state:
            del st.session_state[k]
    for layout in LAYOUT_OPTIONS:
        for suffix in ["n_photo_slots_", "highlight_"]:
            key = f"{suffix}{layout['name']}"
            if key in st.session_state:
                del st.session_state[key]
    st.session_state["url_slots"] = [""]
    st.rerun()

# ============================================================
# HASFLO PINTEREST - PROMPT JSON GENERATOR
# Generate prompt teks siap pakai untuk platform image generator
# (Midjourney, Gemini, ChatGPT, dll)
# ============================================================

import json
import os
from datetime import datetime


def _ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', 4 -> '4th', dst."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def build_prompt_json(
    outfit_type: str,
    subject_description: str,
    layout_name: str,
    layout_description: str,
    n_product_images: int = 2,
    n_photo_slots: int = 3,
    swipe_cta: str = None,
    canvas_size: str = "1000x1500",
    highlight: str = "Full Shot",
    model_name: str = None,
) -> dict:
    """
    Build prompt JSON siap pakai untuk platform image generator eksternal.

    n_product_images : jumlah gambar produk yang diupload sebagai referensi outfit.
    n_photo_slots    : jumlah slot foto dalam collage, dipilih bebas user (3-7).
                       Diinjeksikan langsung ke teks prompt, bukan dari JSON layout.
    swipe_cta        : instruksi swipe spesifik per layout. Fallback ke generik.
    canvas_size      : key dari CANVAS_OPTIONS.
    highlight        : "No Highlight" | "Full Shot" | "Medium Shot"
                       Menentukan jenis hero shot terpisah di luar slot kolase.

    Return: dict JSON
    """

    n_product_images = max(1, int(n_product_images))
    n_photo_slots = max(3, min(7, int(n_photo_slots)))
    use_model = bool(model_name and model_name.strip())

    subject_line = (
        f"consistent subject, {subject_description}"
        if subject_description.strip()
        else "consistent subject, female model with hijab, warm Indonesian face"
    )

    # Jika model diaktifkan: model = upload ke-1, outfit refs mulai dari ke-2
    # Jika tidak: outfit refs mulai dari ke-1 (perilaku lama)
    outfit_start_idx = 2 if use_model else 1
    ordinals = [_ordinal(i) for i in range(outfit_start_idx, outfit_start_idx + n_product_images)]

    if n_product_images == 1:
        product_images_ref = f"the {ordinals[0]} uploaded reference image"
        product_images_plural = "image"
    elif n_product_images == 2:
        product_images_ref = (
            f"the {ordinals[0]} and {ordinals[1]} uploaded reference images"
        )
        product_images_plural = "images"
    else:
        product_images_ref = (
            "the "
            + ", ".join(ordinals[:-1])
            + f", and {ordinals[-1]} uploaded reference images"
        )
        product_images_plural = "images"

    layout_ref_position = _ordinal(outfit_start_idx + n_product_images)
    layout_ref_text = f"the {layout_ref_position} uploaded image (the layout reference)"

    # Instruksi swipe CTA: pakai versi spesifik per-layout kalau tersedia,
    # fallback ke instruksi generik kalau tidak ada.
    swipe_instruction = (
        swipe_cta.strip()
        if swipe_cta and swipe_cta.strip()
        else (
            "Include a small design element with the text 'Swipe' somewhere visible in the "
            "composition — style it naturally according to the layout aesthetic (e.g. sticker "
            "label, torn paper scrap, sticky note, film caption, or handwritten annotation "
            "with arrow)."
        )
    )

    # Resolusi dari pilihan user
    canvas = CANVAS_OPTIONS.get(canvas_size, CANVAS_OPTIONS["1000x1500"])
    canvas_desc = f"{canvas['w']} x {canvas['h']} pixels ({canvas['ratio']} ratio)"

    if highlight == "Full Shot":
        highlight_section = (
            f"\n\nHero shot — Full Shot (separate element, NOT counted in the {n_photo_slots} "
            f"collage slots above): Place one standalone hero photo as a visually dominant "
            f"element in the composition. Frame this hero photo with an organic irregular border "
            f"— torn paper edge, rough hand-cut shape, or dashed outline — that loosely follows "
            f"the rough contour of the subject's body rather than a rectangular or square crop. "
            f"The frame shape should suggest the body outline (wider at shoulders, following the "
            f"general silhouette) without being a precise mask. The subject's full body from head "
            f"to toe must be entirely visible inside the frame — the top of the head, face, hair, "
            f"torso, and feet must all appear within the visible area. The head must never "
            f"disappear behind or outside the frame boundary. Show the complete {outfit_type} "
            f"outfit fully visible. Position this hero photo prominently so it is the first "
            f"element the eye is drawn to."
        )
    elif highlight == "Medium Shot":
        highlight_section = (
            f"\n\nHero shot — Medium Shot (separate element, NOT counted in the {n_photo_slots} "
            f"collage slots above): Place one standalone hero photo as a visually dominant "
            f"element in the composition. Frame this hero photo with an organic irregular border "
            f"— torn paper edge, rough hand-cut shape, or dashed outline — that loosely follows "
            f"the rough contour of the upper body rather than a rectangular crop. The frame shape "
            f"should suggest the body outline from waist up (following shoulders and head area) "
            f"without being a precise mask. The subject's upper body from waist up must be "
            f"entirely visible inside the frame — face, hair, and top of the head must all appear "
            f"within the visible area with space above the head. The head must never disappear "
            f"behind or outside the frame boundary. Show the upper half of the {outfit_type} "
            f"outfit fully visible. Position this hero photo prominently so it is the first "
            f"element the eye is drawn to."
        )
    else:  # No Highlight
        highlight_section = ""

    # Kalimat tegas model reference — hanya muncul jika model diaktifkan
    if use_model:
        # Deteksi apakah subject adalah Indonesian + hijab
        _subj_lower = subject_description.lower()
        _is_hijab = "hijab" in _subj_lower and "no hijab" not in _subj_lower and "without hijab" not in _subj_lower
        _is_indonesian = "indonesian" in _subj_lower

        if _is_indonesian and _is_hijab:
            hair_style_instruction = (
                "The model MUST wear hijab in every photo slot — this is non-negotiable "
                "and must be consistent with the subject description."
            )
        else:
            hair_style_instruction = (
                "Hair style and hair color may vary naturally across photo slots to complement "
                "the outfit aesthetic — straight, wavy, updo, loose, or styled as suits each "
                "shot's mood. Do not lock the hair style to a single look."
            )

        model_anchor = (
            f"⚠️ CRITICAL — MANDATORY MODEL REFERENCE (HIGHEST PRIORITY): "
            f"The 1st uploaded image ({model_name}) is the ONLY face and body reference for "
            f"this entire collage. Every single model appearance in every photo slot — without "
            f"exception — MUST use this exact face, skin tone, and facial features. "
            f"IMPORTANT: The layout reference image (uploaded later) may contain a model or "
            f"face as part of the example — IGNORE that model entirely. Do NOT copy, use, or "
            f"be influenced by the face or body shown in the layout reference image. "
            f"The layout reference is used SOLELY for composition structure, photo slot "
            f"arrangement, and design style — the face/model inside it is irrelevant and must "
            f"be disregarded. The face from the 1st uploaded image is ABSOLUTE and cannot be "
            f"replaced, blended, or altered by any other image in this prompt. "
            f"If the outfit reference images show the outfit without a model or head, "
            f"generate the body and pose naturally — but the face MUST always come from "
            f"the 1st uploaded image, no exceptions. "
            f"{hair_style_instruction}\n\n"
        )
    else:
        model_anchor = ""

    prompt = f"""{model_anchor}Create an irregular layered photo collage at {canvas_desc}, scrapbook style mixed-media montage using {product_images_ref} as outfit reference. Follow the collage layout style shown in {layout_ref_text}.

Subject: {subject_line}, wearing {outfit_type} outfit. Preserve every detail of the {outfit_type} accurately including color and fabric texture. Optionally add "Hasflo" or "HASFLO" text somewhere in the composition, but it is not mandatory.

Outfit reference handling: The uploaded outfit reference images may show the outfit without a model (flat lay, mannequin, or headless product photo). In that case, generate a realistic full-body model wearing the outfit based on the subject description above — create a natural, original face and body. NEVER use or be influenced by any face, model, or character visible in the layout reference image under any circumstances. The layout reference is strictly for composition structure only.

Photo slots: create exactly {n_photo_slots} collage photo slots following the composition style and scale hierarchy shown in {layout_ref_text}. Each slot should contain the {outfit_type} outfit as the focus, with content varying naturally by slot purpose — full-body shots, half-body, close-up fabric or collar detail, back view, or accessory detail as appropriate to each slot's size and position in the composition. If the layout reference includes a freeform cutout or silhouette element as a separate compositional layer (not a framed photo slot), treat that as an additional element outside the {n_photo_slots} count.{highlight_section}

Layout reference style: {layout_description}

Swipe CTA (mandatory): {swipe_instruction}

Style: overlapping photos stacked, clean white borders, balanced layout, generous negative space, premium typography placeholders, subtle doodle elements, soft shadows, cohesive storytelling. Let the location, atmosphere, and color palette follow the layout reference style above.

Photography: luxury fashion campaign, Pinterest aesthetic, Zara campaign, Sezane editorial, Maison Kitsuné lookbook, high-end modest fashion photography. Ultra realistic, commercial quality, DSLR photography, Canon EOS R5, RF 50mm f/1.2 lens, shallow depth of field, cinematic natural lighting, HDR, extremely detailed fabric texture, crisp focus, color accurate, premium retouching, magazine quality, 8K resolution.

Avoid: low quality, blurry, overprocessed skin, AI artifacts, extra fingers, distorted hands, duplicated limbs, incorrect outfit design, bad anatomy, unrealistic face, plastic skin, oversaturated colors, harsh lighting, watermark, poor composition, cartoon style, illustration style, CGI look, low resolution, grid layout, perfect symmetry, flat composition."""

    # Urutan upload yang harus diikuti user, dipakai untuk panduan "Cara pakai" di UI
    upload_order = {}
    if use_model:
        upload_order["upload_1"] = (
            f"🧑 MODEL REFERENCE ({model_name}) — upload PERTAMA "
            f"(disebut sebagai '1st uploaded image' di prompt)"
        )
    for idx in range(1, n_product_images + 1):
        slot_num = idx + (1 if use_model else 0)
        upload_order[f"upload_{slot_num}"] = (
            f"gambar produk scrapped ke-{idx} dari {n_product_images} — sebagai referensi outfit "
            f"(disebut sebagai '{ordinals[idx - 1]} uploaded reference image' di prompt)"
        )
    upload_order["upload_terakhir"] = (
        f"gambar layout referensi ({layout_name}) — upload PALING TERAKHIR "
        f"(disebut sebagai '{layout_ref_position} uploaded image' di prompt)"
    )

    return {
        "prompt": prompt,
        "placeholders": upload_order,
        "settings": {
            "outfit_type": outfit_type,
            "subject": subject_description
            or "female model with hijab, warm Indonesian face",
            "layout_selected": layout_name,
            "model_reference": model_name if use_model else None,
            "n_product_images": n_product_images,
            "n_photo_slots": n_photo_slots,  # user-defined, reflected in prompt
            "total_images_to_upload": n_product_images + 1 + (1 if use_model else 0),
            "aspect_ratio_recommended": f"{canvas['ratio']} — {canvas['w']} x {canvas['h']} pixels",
            "platform_notes": (
                (
                    f"Upload MODEL REFERENCE ({model_name}) dulu sebagai gambar pertama, "
                    f"lalu {n_product_images} gambar produk, "
                    "lalu gambar layout referensi paling terakhir, baru paste prompt ini."
                )
                if use_model else (
                    f"Upload {n_product_images} gambar produk dulu sesuai urutan, "
                    "lalu gambar layout referensi paling terakhir, baru paste prompt ini."
                )
            ),
        },
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


def save_prompt_json(prompt_dict: dict, output_dir: str = "output") -> str:
    """Simpan prompt JSON (lengkap dengan metadata) ke file dan return filepath.
    Berguna untuk arsip internal, BUKAN untuk dipaste ke platform image generator."""
    os.makedirs(os.path.join(output_dir, "prompts"), exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, "prompts", f"prompt_{timestamp}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(prompt_dict, f, indent=2, ensure_ascii=False)
    return filepath


def save_prompt_text(prompt_text: str, output_dir: str = "output") -> str:
    """Simpan teks prompt MURNI (tanpa metadata/placeholders) ke file .txt.
    Inilah file yang dimaksudkan untuk di-copy-paste langsung ke platform
    image generator (Midjourney, Gemini, ChatGPT, dll)."""
    os.makedirs(os.path.join(output_dir, "prompts"), exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, "prompts", f"prompt_{timestamp}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(prompt_text)
    return filepath


# ============================================================

# ============================================================
# CANVAS OPTIONS
# ============================================================

CANVAS_OPTIONS = {
    "1000x1500": {"label": "1000 × 1500 px (2:3 — Pinterest vertikal)", "ratio": "2:3",  "w": 1000, "h": 1500},
    "1080x1440": {"label": "1080 × 1440 px (3:4)",                       "ratio": "3:4",  "w": 1080, "h": 1440},
    "1500x1500": {"label": "1500 × 1500 px (1:1 — Square)",              "ratio": "1:1",  "w": 1500, "h": 1500},
    "1080x1920": {"label": "1080 × 1920 px (9:16 — Stories / Reels)",    "ratio": "9:16", "w": 1080, "h": 1920},
}

# ============================================================
# LAYOUT LOADER — scan folder assets/ secara otomatis
# JSON dan preview image (.jpg) berada di folder yang sama.
# Menambah layout baru = taruh layoutN.json + layoutN.jpg di assets/
# ============================================================

import glob
import pathlib


def load_layouts(assets_dir: str = "assets") -> list:
    """
    Load semua file JSON dari folder assets/ secara otomatis.
    Setiap layoutN.json dipairing dengan layoutN.jpg di folder yang sama.
    preview_path di-derive otomatis dari nama file — tidak perlu ditulis
    manual di JSON (tapi kalau ada, tetap dihormati).

    Urutan ditentukan oleh field "order" di JSON (int, opsional).
    Fallback: alphabetical by filename.

    Return: list of dict (format identik dengan LAYOUT_OPTIONS lama)
    """
    pattern = os.path.join(assets_dir, "*.json")
    files = sorted(glob.glob(pattern))

    layouts = []
    for filepath in files:
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            stem = pathlib.Path(filepath).stem          # "layout1"
            # preview_path: selalu resolve ke assets/<stem>.jpg
            # Tulis di JSON hanya kalau nama jpg berbeda dari stem
            if "preview_path" not in data:
                data["preview_path"] = f"{assets_dir}/{stem}.jpg"

            layouts.append(data)
        except Exception as e:
            print(f"[layout_loader] Skip {filepath}: {e}")

    # Sort: utamakan field "order" kalau ada, fallback nama file
    layouts.sort(key=lambda x: (x.get("order", 9999), x.get("name", "")))

    return layouts


# LAYOUT_OPTIONS di-load otomatis saat modul diimport.
LAYOUT_OPTIONS = load_layouts()

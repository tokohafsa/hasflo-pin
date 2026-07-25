# ============================================================
# HASFLO PINTEREST - PROCESSOR
# Logika board, keyword, jadwal, AI, dan generate CSV
# ============================================================

import os
import json

from config import (
    BOARD_SECTIONS,
    PRODUCT_KEYWORDS,
    OUTPUT_DIR,
)
from _credentials import AI_ENABLED, AI_API_KEY, AI_MODEL
from templates import get_title, get_desc



# ============================================================
# DETEKSI TIPE PRODUK
# ============================================================


def detect_product_type(judul: str) -> str:
    """
    Deteksi tipe produk dari judul asli Shopee.
    Return: 'dress' | 'blouse' | 'tunik' | 'outer' | 'setelan' | 'unknown'
    """
    judul_lower = judul.lower()
    for tipe, keywords in PRODUCT_KEYWORDS.items():
        if any(kw in judul_lower for kw in keywords):
            return tipe
    return "unknown"


def get_board(product_type: str) -> str:
    return BOARD_SECTIONS.get(product_type, "Fashion Outfit Modern Motif Bunga")


# ============================================================
# GENERATE TITLE & DESCRIPTION
# ============================================================


def ai_generate(judul_shopee: str, desc_shopee: str, product_type: str, used_titles: set = None) -> tuple:
    """
    Panggil Gemini API (SDK Baru) untuk generate title & description.
    Return: (title, description)
    """
    try:
        from google import genai

        client = genai.Client(api_key=AI_API_KEY)

        used_titles_str = "\n".join(f"- {t}" for t in (used_titles or set()))
        prompt = f"""Kamu adalah asisten untuk membuat konten Pinterest untuk akun fashion wanita bermotif bunga.

Judul produk Shopee: {judul_shopee}
Deskripsi produk Shopee: {desc_shopee}
Tipe produk: {product_type}

JUDUL YANG SUDAH DIPAKAI DAN TIDAK BOLEH DIGUNAKAN LAGI:
{used_titles_str if used_titles_str else "(belum ada)"}

ATURAN WAJIB:
1. Title HARUS BERBEDA dari semua judul yang sudah dipakai di atas
2. Title max 100 karakter, natural, tidak hard selling, campuran Indonesia-Inggris boleh
3. Description max 500 karakter, faktual, tidak persuasif, tidak ada kata sales marketing

Format output HANYA JSON:
{{"title": "...", "description": "..."}}"""

        response = client.models.generate_content(model=AI_MODEL, contents=prompt)

        # Membersihkan output jika ada markdown backticks (```json ... ```)
        text = response.text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)
        return (data["title"], data["description"])

    except Exception as e:
        print(f"Error pada Gemini: {e}")
        return ("Default Title", "Default Description")


def generate_title_desc(
    judul_shopee: str, desc_shopee: str, product_type: str, index: int, used_titles: set = None
) -> tuple:
    """
    Generate title & description.
    Pakai AI kalau aktif, fallback ke template kalau tidak.
    """
    if AI_ENABLED and AI_API_KEY:
        title, desc = ai_generate(judul_shopee, desc_shopee, product_type, used_titles)
        if title != "Default Title" and desc != "Default Description":
            return title, desc

    # Fallback template
    return get_title(product_type, index), get_desc(product_type, index)


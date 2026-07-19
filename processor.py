# ============================================================
# HASFLO PINTEREST - PROCESSOR
# Logika board, keyword, jadwal, AI, dan generate CSV
# ============================================================

import csv
import random
import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import (
    AI_MODEL,
    BOARD_SECTIONS,
    PRODUCT_KEYWORDS,
    KEYWORDS,
    RANDOM_TIME_MIN_WIB,
    RANDOM_TIME_MAX_WIB,
    SCHEDULE_BUFFER_MINUTES,
    OUTPUT_DIR,
)
from _credentials import AI_ENABLED, AI_API_KEY

WIB = ZoneInfo("Asia/Jakarta")
UTC = ZoneInfo("UTC")


# ============================================================
# DETEKSI TIPE PRODUK
# ============================================================


def detect_product_type(judul: str) -> str:
    judul_lower = judul.lower()
    for tipe, keywords in PRODUCT_KEYWORDS.items():
        if any(kw in judul_lower for kw in keywords):
            return tipe
    return "unknown"


def get_board(product_type: str) -> str:
    return BOARD_SECTIONS.get(product_type, "Floral Fashion Picks")


def get_keyword(product_type: str) -> str:
    if product_type == "dress":
        return KEYWORDS["dress"]
    return KEYWORDS["default"]


# ============================================================
# GENERATE TITLE & DESCRIPTION
# ============================================================


def ai_generate(judul_shopee: str, desc_shopee: str, product_type: str, used_titles: set = None) -> tuple:
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
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return (data["title"], data["description"])

    except Exception as e:
        print(f"Error pada Gemini: {e}")
        return ("Default Title", "Default Description")


def generate_title_desc(
    judul_shopee: str, desc_shopee: str, product_type: str, index: int, used_titles: set = None
) -> tuple:
    if AI_ENABLED and AI_API_KEY:
        title, desc = ai_generate(judul_shopee, desc_shopee, product_type, used_titles)
        if title != "Default Title" and desc != "Default Description":
            return title, desc

    from templates import get_title, get_desc
    return get_title(product_type, index), get_desc(product_type, index)


# ============================================================
# SCHEDULING
# ============================================================


def parse_schedule_instruction(instruction: str, total_pins: int) -> list:
    if AI_ENABLED and AI_API_KEY:
        try:
            from google import genai

            client = genai.Client(api_key=AI_API_KEY)

            now_wib = datetime.now(WIB)
            min_time_wib = now_wib + timedelta(minutes=SCHEDULE_BUFFER_MINUTES)

            prompt = f"""Kamu adalah asisten untuk mengatur jadwal posting Pinterest.

Waktu sekarang (WIB): {now_wib.strftime('%Y-%m-%d %H:%M')}
Waktu minimum publish (WIB, sudah include buffer 2 jam): {min_time_wib.strftime('%Y-%m-%d %H:%M')}
Total pin yang akan dijadwalkan: {total_pins}

Instruksi dari user: "{instruction}"

Aturan:
- Urutan Random, tidak boleh publish time urut dari 1 sd terakhir
- Semua waktu harus setelah waktu minimum publish
- Output dalam UTC (WIB - 7 jam)
- Jika instruksi menyebut "now" atau "langsung", gunakan string kosong ""
- Jika instruksi menyebut "random", acak dalam range jam yang disebutkan
- Format datetime: YYYY-MM-DDTHH:MM:SS

Output HANYA JSON array dengan panjang {total_pins}:
["2026-06-27T02:00:00", "", "2026-06-28T07:30:00", ...]"""

            response = client.models.generate_content(model=AI_MODEL, contents=prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            schedule = json.loads(text)
            return schedule

        except Exception as e:
            print(f"[AI SCHEDULE ERROR] {e} — fallback ke default")

    return generate_schedule_default(total_pins)


def generate_schedule_default(total_pins: int, interval_days: int = 1) -> list:
    now_wib = datetime.now(WIB)
    min_time = now_wib + timedelta(minutes=SCHEDULE_BUFFER_MINUTES)
    start = min_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    schedule = []
    for i in range(total_pins):
        day = start + timedelta(days=i * interval_days)
        hour_wib = random.randint(RANDOM_TIME_MIN_WIB, RANDOM_TIME_MAX_WIB)
        minute = random.choice([0, 15, 30, 45])
        dt_wib = day.replace(hour=hour_wib, minute=minute, second=0, microsecond=0)
        dt_utc = dt_wib.astimezone(UTC)
        schedule.append(dt_utc.strftime("%Y-%m-%dT%H:%M:%S"))

    return schedule


# ============================================================
# GENERATE CSV
# ============================================================


def generate_csv(pins: list, schedule: list, filename: str = None) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hasflo_pins_{timestamp}.csv"

    filepath = os.path.join(OUTPUT_DIR, filename)

    type_counters = {}

    combined = list(zip(pins, schedule))
    random.shuffle(combined)
    pins, schedule = zip(*combined) if combined else ([], [])
    pins = list(pins)
    schedule = list(schedule)

    used_titles = set()
    rows = []
    for i, pin in enumerate(pins):
        tipe = pin.get("product_type", "unknown")
        type_counters[tipe] = type_counters.get(tipe, 0)

        max_attempts = 20
        for attempt in range(max_attempts):
            title, desc = generate_title_desc(
                pin["judul_shopee"], pin.get("desc_shopee", ""), tipe, type_counters[tipe], used_titles
            )
            type_counters[tipe] += 1
            if title not in used_titles:
                break
            print(f"[CSV] Duplikat title '{title}', coba variasi lain (attempt {attempt+1})")
        else:
            suffix = type_counters[tipe]
            title = f"{title} {suffix}"

        used_titles.add(title)

        media_type = pin.get("media_type", "image")
        thumbnail = pin.get("thumbnail", "")

        rows.append([
            title,
            pin["media_url"],
            get_board(tipe),
            thumbnail,
            desc,
            pin["affiliate_link"],
            schedule[i] if i < len(schedule) else "",
            get_keyword(tipe),
        ])

    rows.sort(key=lambda x: x[0].lower())

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\r\n")
        writer.writerow([
            "Title", "Media URL", "Pinterest board", "Thumbnail",
            "Description", "Link", "Publish date", "Keywords",
        ])
        writer.writerows(rows)

    return filepath

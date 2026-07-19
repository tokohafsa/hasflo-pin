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
    AI_ENABLED,
    AI_API_KEY,
    AI_MODEL,
    BOARD_SECTIONS,
    PRODUCT_KEYWORDS,
    KEYWORDS,
    RANDOM_TIME_MIN_WIB,
    RANDOM_TIME_MAX_WIB,
    SCHEDULE_BUFFER_MINUTES,
    OUTPUT_DIR,
)
from templates import get_title, get_desc

WIB = ZoneInfo("Asia/Jakarta")
UTC = ZoneInfo("UTC")


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
    return BOARD_SECTIONS.get(product_type, "Floral Fashion Picks")


def get_keyword(product_type: str) -> str:
    if product_type == "dress":
        return KEYWORDS["dress"]
    return KEYWORDS["default"]


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


# ============================================================
# SCHEDULING
# ============================================================


def parse_schedule_instruction(instruction: str, total_pins: int) -> list:
    """
    Parse instruksi jadwal natural language via Gemini API (SDK Baru).
    Return: list datetime UTC untuk setiap pin.
    Fallback ke default kalau AI tidak aktif.
    """
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
- Urutan Random, tidak boleh publish time urut dari 1 sd terakhir, bisa dari akhir dulu, atau awal dulu, atau even dulu, odd dulu, awal lalu akhir lalu tengah
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

    # Fallback: harian random
    return generate_schedule_default(total_pins)


def generate_schedule_default(total_pins: int, interval_days: int = 1) -> list:
    """
    Generate jadwal default: harian, jam random WIB dalam range config.
    Return: list string datetime UTC.
    """
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
    """
    Generate CSV Pinterest bulk upload.

    pins: list of dict {
        'judul_shopee': str,
        'desc_shopee': str,
        'media_url': str,
        'affiliate_link': str,
        'product_type': str,   # hasil detect_product_type()
    }
    schedule: list of str datetime UTC (atau "" untuk now)
    filename: nama file output (opsional)

    Return: path file CSV yang digenerate
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hasflo_pins_{timestamp}.csv"

    filepath = os.path.join(OUTPUT_DIR, filename)

    # Track index per tipe untuk rotasi template
    type_counters = {}

    # Shuffle pins + schedule bersamaan agar tetap sinkron
    import random
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

        # Generate title unik — tidak boleh duplikat dalam satu batch
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
            # Jika semua variasi habis, tambahkan suffix unik
            suffix = type_counters[tipe]
            title = f"{title} {suffix}"
            print(f"[CSV] Fallback title dengan suffix: {title}")

        used_titles.add(title)

        # Support image dan video
        media_type = pin.get("media_type", "image")
        thumbnail = pin.get("thumbnail", "")  # "0:05" untuk video, kosong untuk image

        rows.append(
            [
                title,
                pin["media_url"],
                get_board(tipe),
                thumbnail,
                desc,
                pin["affiliate_link"],
                schedule[i] if i < len(schedule) else "",
                get_keyword(tipe),
            ]
        )

    # Sort berdasarkan Title A-Z
    rows.sort(key=lambda x: x[0].lower())

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\r\n")
        writer.writerow(
            [
                "Title",
                "Media URL",
                "Pinterest board",
                "Thumbnail",
                "Description",
                "Link",
                "Publish date",
                "Keywords",
            ]
        )
        writer.writerows(rows)

    return filepath

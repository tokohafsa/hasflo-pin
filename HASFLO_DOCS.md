# HASflo Prompt Generator — Dokumentasi Lengkap

> Terakhir diupdate: Oktober 2026  
> Deploy: https://hasflo-pin.streamlit.app  
> Repo: https://github.com/tokohafsa/hasflo-pin

---

## Daftar Isi

1. [Overview](#1-overview)
2. [Struktur File](#2-struktur-file)
3. [Alur Pipeline Lengkap](#3-alur-pipeline-lengkap)
4. [App — Step by Step](#4-app--step-by-step)
5. [image_generator.py](#5-image_generatorpy)
6. [Dropbox Client](#6-dropbox-client)
7. [Credentials & Config](#7-credentials--config)
8. [Sistem Layout](#8-sistem-layout)
9. [Model Reference](#9-model-reference)
10. [Board & Section Routing](#10-board--section-routing)
11. [Otomasi Pipeline](#11-otomasi-pipeline)
12. [Postiz Setup](#12-postiz-setup)
13. [Pinterest Agent](#13-pinterest-agent)
14. [Catatan Teknis](#14-catatan-teknis)

---

## 1. Overview

HASflo Prompt Generator adalah aplikasi Streamlit internal untuk akun Pinterest affiliate fashion **HAS_flo** (`pinterest.com/HAS_flo`). Akun ini fokus pada konten fashion wanita bermotif bunga untuk audiens Indonesia, dimonetisasi via Shopee affiliate links.

**Tujuan aplikasi:** menghasilkan prompt teks siap pakai untuk platform image generator (ChatGPT/GPT-4o, Midjourney, Gemini) yang akan menghasilkan collage foto fashion gaya scrapbook/Pinterest dari foto produk Shopee, sekaligus generate judul & deskripsi Pinterest via Gemini AI.

**Output akhir:** folder `ready_pin/` di Dropbox berisi gambar carousel + metadata, siap dipost ke Pinterest oleh agent otomasi.

---

## 2. Struktur File

```
hasflo-pin/
├── app.py                  — Streamlit UI utama (10 step)
├── image_generator.py      — build_prompt_json(), load layout, canvas options
├── dropbox_client.py       — upload/rename/list Dropbox via OAuth2
├── _credentials.py         — baca secrets dari st.secrets (Streamlit Cloud)
├── config.py               — konstanta non-secret (OUTPUT_DIR, BOARD_SECTIONS, dll)
├── processor.py            — CSV bulk upload untuk single-image pin (legacy)
├── title_desc_generator.py — section judul & deskripsi terpisah (legacy)
├── templates.py            — pool title/desc per tipe produk (fallback tanpa AI)
├── scraper.py              — Playwright scraper Shopee (jalankan lokal)
├── requirements.txt
├── assets/
│   ├── layout4.json + layout4.jpg
│   ├── layout5.json + layout5.jpg
│   └── ...                 — tambah layout baru = taruh JSON + JPG di sini
├── assets/models/
│   └── [nama].jpg          — foto model referensi (konvensi nama: lihat §9)
└── output/                 — output CSV bulk upload
```

### Kredensial (st.secrets / .streamlit/secrets.toml)

| Key | Keterangan |
|-----|-----------|
| `AI_API_KEY` | Google Gemini API key |
| `AI_MODEL` | Model Gemini (default: `gemini-2.0-flash-lite`) |
| `DROPBOX_APP_KEY` | Dropbox OAuth2 App Key |
| `DROPBOX_APP_SECRET` | Dropbox OAuth2 App Secret |
| `DROPBOX_REFRESH_TOKEN` | Dropbox OAuth2 Refresh Token |
| `DROPBOX_FOLDER` | Root folder Dropbox (default: `/Apps/SVGI Pinterest/HASflo`) |

---

## 3. Alur Pipeline Lengkap

```
[Shopee produk]
      │
      ▼
[app.py — 10 step]
      │
      ├─ Generate judul + deskripsi Pinterest via Gemini
      ├─ Generate prompt collage (image_generator.py)
      │
      ▼
[Dropbox: bahan_prompt/]
      │  prompt.txt, imageN.jpg, layout.jpg, _model_ref.jpg
      ▼
[User: upload ke ChatGPT → dapat hasil collage]
      │
      ▼
[app.py Step 10: drag hasil GPT]
      │
      ▼
[Dropbox: READY_{folder}/ready_pin/]
      │  slides/slide1.jpg, image1.jpg, image2.jpg, deskripsi.txt
      ▼
[pinterest_agent.py — otomasi]
      │  poll Dropbox → post carousel → rename DONE/
      ▼
[Pinterest: carousel pin published]
```

---

## 4. App — Step by Step

### Step 1 — Link Affiliate Shopee *(wajib)*

- Input link affiliate Shopee sebelum bisa lanjut ke step berikutnya
- Auto-strip: trailing dot dan query string (`?channel_type=...`)
- Ditampilkan sebagai clickable link setelah diisi
- Nilai ini masuk ke `deskripsi.txt` baris 4 di `ready_pin/`

---

### Step 2 — Input URL Gambar Produk

- Satu URL Shopee CDN per field; slot baru muncul otomatis setelah field terisi
- Suffix `@resize_xxx` di-strip otomatis via regex
- Preview thumbnail ditampilkan per URL
- Selectbox **canvas size** muncul di bawah preview (default: random saat pertama load)
- Tombol **🗑️ Clear Semua** mereset seluruh session state dan URL slots

**Canvas options:**

| Key | Ukuran | Ratio | Prefix folder |
|-----|--------|-------|---------------|
| `1000x1500` | 1000×1500 px | 2:3 | `[2x3]` |
| `1080x1440` | 1080×1440 px | 3:4 | `[3x4]` |
| `1500x1500` | 1500×1500 px | 1:1 | `[1x1]` |
| `1080x1920` | 1080×1920 px | 9:16 | `[9x16]` |

---

### Step 3 — Judul Produk & Generate Title Pinterest

**Flow 3 tahap:**

1. Input judul produk dari Shopee
2. Klik **🔍 Cek Judul** → deteksi tipe outfit via Gemini AI (fallback: keyword matching)
3. Konfirmasi tipe + pilih Hijab/Non-Hijab → klik **✨ Generate Judul & Deskripsi**

**Auto-detect tipe produk:**

| Tipe | Keywords |
|------|----------|
| `dress` | dress, gamis, terusan |
| `blouse` | blouse, atasan, kemeja |
| `tunik` | tunik |
| `outer` | outer, jaket, cardigan, sweater |
| `setelan` | setelan, one set, co-ord |
| fallback | `dress` |

**Board routing (Step 3B):**

- Tunik → selalu Board Hijab, tidak bisa override
- Selain tunik: ikut pilihan Hijab/Non-Hijab user
- Board & section disimpan ke session state untuk Step 10

**Prompt Gemini untuk judul:**
- Format wajib: `[Tipe Outfit] + "Motif Bunga" + ciri khas (bahan/potongan/warna)`
- Contoh: `"Dress Motif Bunga Midi Rayon Lengan Panjang"`
- Max 100 karakter; "OOTD" tidak masuk judul

**Prompt Gemini untuk deskripsi:**
- Kalimat 1: judul Shopee verbatim (wajib, tidak diubah)
- Kalimat 2: wajib mengandung "OOTD" dan "motif bunga"
- Kalimat 3–4: min 3 keyword dari SEO_KEYWORDS secara natural
- Max 500 karakter; bahasa Indonesia, faktual, tidak persuasif
- Dilarang: "dapatkan sekarang", "segera beli", "promo", dll

Hasil bisa diedit langsung di text area sebelum lanjut.

---

### Step 4 — Model Reference *(opsional)*

- Toggle default OFF
- Saat aktif: scan `assets/models/` otomatis, filter berdasarkan hijab status
- Preview foto model ditampilkan setelah dipilih
- File model yang dipilih akan diupload ke ChatGPT sebagai gambar pertama
- Konvensi naming file: lihat [§9 Model Reference](#9-model-reference)

---

### Step 5 — Deskripsi Subject

Menentukan deskripsi model yang akan di-generate AI.

| Kondisi | Nationality tersedia |
|---------|---------------------|
| Hijab ON | Indonesian (terkunci) |
| Hijab OFF | Indonesian, Japanese, Korean |

- Usia: 18 / 25 / 33 years old
- Opsi **tulis sendiri** menggantikan pilihan dropdown jika diisi
- Output contoh: `female, warm Indonesian face, wearing hijab, 25 years old`

---

### Step 6 — Pilih Layout Collage

- Layout di-load otomatis dari `assets/*.json`
- Tampilan: 2 kolom, border highlight untuk layout aktif
- Per layout: selectbox **jumlah photo slot** (3–7) dan radio **hero shot mode**

**Hero shot options:**
- `Full Shot` — full body head-to-toe, organic irregular border frame
- `Medium Shot` — upper body waist-up, organic irregular border frame
- `No Highlight` — tidak ada hero shot terpisah

---

### Step 7 — Generate Prompt

- Tombol **✨ Generate Prompt** memanggil `build_prompt_json()` dari `image_generator.py`
- Output disimpan ke `session_state["last_prompt_json"]`
- Tombol disabled jika belum ada URL gambar

---

### Step 8 — Hasil Prompt

- Tampilkan judul & deskripsi Pinterest (jika sudah digenerate)
- Prompt collage ditampilkan dalam expander (collapsed by default)
- Preview gambar outfit refs + layout preview
- Urutan upload gambar ke platform ditampilkan sebagai panduan

---

### Step 9 — Upload Bahan Prompt ke Dropbox

- **Copy prompt** tersedia via `st.code` (tombol copy built-in) tepat di atas tombol upload
- Tombol **☁️ Upload Bahan Prompt ke Dropbox**:
  1. Fetch tiap gambar outfit dari Shopee CDN
  2. Upload model ref (jika aktif) ke `bahan_prompt/_model_ref.xxx`
  3. Upload layout preview ke `bahan_prompt/layout.jpg`
  4. Upload `prompt.txt`
  5. Simpan `_folder_name` dan `_outfit_files` ke session state

**Nama folder Dropbox:**
```
{[RATIOxRATIO]}{20_char_judul}_{YYYYMMDD}
Contoh: [2x3]Dress_Wanita_Motif_B_20261019
```

**Struktur `bahan_prompt/`:**
```
bahan_prompt/
├── _model_ref.jpg      (jika model aktif — diupload pertama)
├── image1.jpg          (outfit ref 1, atau image2 jika model aktif)
├── image2.jpg          (outfit ref 2, dst)
├── layout.jpg          (layout reference — selalu paling akhir)
└── prompt.txt          (prompt teks — paste ke ChatGPT)
```

Urutan upload ke ChatGPT mengikuti urutan file di atas — model ref dulu, baru outfit refs, baru layout.

Setelah upload sukses: tombol **🤖 Buka ChatGPT** muncul.

---

### Step 10 — Upload Hasil GPT & Kirim Ready Pin

- Drag & drop gambar hasil GPT (Slide 1)
- Preview urutan slide carousel dengan opsi **expand** (dominant color fill) atau **crop** (center crop) per outfit ref slide
- Tombol **☁️ Upload Ready Pin ke Dropbox**:
  1. Upload `slides/slide1.jpg` (hasil GPT, as-is)
  2. Upload outfit refs yang sudah diproses Pillow (expand/crop sesuai canvas)
  3. Upload `deskripsi.txt`
  4. Rename folder parent: `{folder}` → `READY_{folder}`

**Struktur `ready_pin/`:**
```
ready_pin/
├── slides/
│   └── slide1.jpg      (hasil GPT — slide utama)
├── image1.jpg          (outfit ref 1)
├── image2.jpg          (outfit ref 2, dst)
└── deskripsi.txt       (4 baris flat)
```

**Format `deskripsi.txt` (4 baris — TIDAK BOLEH diubah):**
```
Fashion Outfit Hijab Motif Bunga/Dress
Dress Motif Bunga Midi Rayon Lengan Panjang
Dress Wanita Motif Bunga Premium Rayon... (deskripsi Pinterest)
https://shope.ee/xxxx
```

---

## 5. image_generator.py

### `build_prompt_json()`

**Parameter:**

| Parameter | Tipe | Keterangan |
|-----------|------|-----------|
| `outfit_type` | str | Tipe outfit: dress, blouse, tunik, outer, setelan |
| `subject_description` | str | Deskripsi model subject |
| `layout_name` | str | Nama layout aktif |
| `layout_description` | str | Deskripsi layout dari JSON |
| `n_product_images` | int | Jumlah gambar outfit ref (min 1) |
| `n_photo_slots` | int | Jumlah slot foto collage (3–7) |
| `swipe_cta` | str\|None | Instruksi swipe custom dari layout JSON |
| `canvas_size` | str | Key canvas: "1000x1500", "1080x1440", dll |
| `highlight` | str | "Full Shot", "Medium Shot", "No Highlight" |
| `model_name` | str\|None | Nama model reference (None = tidak pakai) |

**Return:** dict dengan keys:
- `prompt` — teks prompt lengkap siap paste
- `placeholders` — urutan upload file ke GPT
- `settings` — metadata (outfit_type, layout, n_photo_slots, canvas, dll)
- `generated_at` — timestamp

### `load_layouts()`

Scan semua `*.json` di folder `assets/`, auto-pair dengan `*.jpg` nama sama. Sort berdasarkan field `order` di JSON.

---

## 6. Dropbox Client

File: `dropbox_client.py`

| Fungsi | Keterangan |
|--------|-----------|
| `_get_access_token()` | Tukar refresh token → access token baru (~4 jam) |
| `upload_bytes()` | Upload bytes in-memory ke Dropbox |
| `upload_file()` | Upload file lokal ke Dropbox |
| `upload_folder()` | Upload folder rekursif dengan progress callback |
| `rename_folder()` | Rename/move folder (dipakai untuk prefix READY_/DONE_) |
| `list_subfolders()` | List subfolder langsung di bawah path tertentu |

Semua fungsi menerima `access_token` dari `_get_access_token()` — dipanggil fresh tiap sesi, tidak disimpan ke disk.

---

## 7. Credentials & Config

### `_credentials.py`

Baca dari `st.secrets` (Streamlit Cloud) atau `.streamlit/secrets.toml` (lokal):

```python
AI_ENABLED            = True
AI_API_KEY            = st.secrets["AI_API_KEY"]
AI_MODEL              = st.secrets.get("AI_MODEL", "gemini-2.0-flash-lite")
DROPBOX_APP_KEY       = st.secrets["DROPBOX_APP_KEY"]
DROPBOX_APP_SECRET    = st.secrets["DROPBOX_APP_SECRET"]
DROPBOX_REFRESH_TOKEN = st.secrets["DROPBOX_REFRESH_TOKEN"]
DROPBOX_FOLDER        = st.secrets.get("DROPBOX_FOLDER", "/Apps/SVGI Pinterest/HASflo")
```

### `config.py`

Konstanta non-secret: `AI_IMAGE_MODEL`, `OUTPUT_DIR`, `BOARD_SECTIONS`, `PRODUCT_KEYWORDS`.

---

## 8. Sistem Layout

Layout di-load otomatis dari `assets/`. Tidak perlu ubah kode untuk menambah layout baru.

**Cara menambah layout:**
1. Simpan file JSON: `assets/layoutN.json`
2. Simpan preview JPG: `assets/layoutN.jpg` (nama stem harus sama)

**Field JSON layout:**

| Field | Tipe | Keterangan |
|-------|------|-----------|
| `name` | str | Nama layout (ditampilkan di UI) |
| `description` | str | Deskripsi gaya untuk diinjeksi ke prompt |
| `tags` | list[str] | Tag visual (contoh: `["scrapbook", "clean"]`) |
| `order` | int | Urutan tampil di UI (ascending) |
| `n_photo_slots` | int | Default jumlah slot (3–7) |
| `swipe_cta` | str\|None | Instruksi swipe custom (opsional) |
| `preview_path` | str\|None | Auto-derive dari stem jika tidak diisi |

---

## 9. Model Reference

File model disimpan di `assets/models/`. Konvensi nama file menentukan filter hijab:

| Prefix nama file | Muncul di |
|-----------------|-----------|
| `indohijab*` | Board Hijab (Indonesian) |
| `indo*` | Board Modern (Indonesian) |
| `asian*` | Board Modern (Korean/Chinese/Japanese) |
| `asianhijab*` | Board Hijab (Asian) |

- Ekstensi case-insensitive: `.png`, `.PNG`, `.jpg`, `.JPG`, `.jpeg`, `.JPEG`, `.webp`, `.WEBP`
- **Rename ke lowercase** untuk menghindari bug di Linux/Streamlit Cloud
- Tambah model baru = upload file ke `assets/models/`, auto-terdeteksi tanpa ubah kode
- Path wajib pakai `os.path.dirname(os.path.abspath(__file__))` — Streamlit Cloud gagal resolve relative path

**Nationality logic berdasarkan nama model:**

| Kondisi | Nationality tersedia |
|---------|---------------------|
| Toggle OFF + Hijab | Indonesian (terkunci) |
| Toggle OFF + Non-hijab | Indonesian, Japanese, Korean |
| Toggle ON + nama starts "indo" | Indonesian (terkunci) |
| Toggle ON + nama starts "asian" | Korean, Chinese, Japanese |

---

## 10. Board & Section Routing

| Board | Sections |
|-------|---------|
| `Fashion Outfit Hijab Motif Bunga` | Dress, Blouse, Tunik, One Set, Outer |
| `Fashion Outfit Modern Motif Bunga` | Dress, Blouse, One Set, Outer |

**Rules:**
- Tunik → selalu Board Hijab, tidak bisa override
- Setelan → Section "One Set" di kedua board
- Board/section disimpan ke `deskripsi.txt` baris 1 untuk dibaca agent

---

## 11. Otomasi Pipeline

### Komponen

| Komponen | Peran |
|----------|-------|
| Streamlit Cloud | Host app.py |
| Dropbox | Bridge lintas device; folder `READY_` = antrian posting |
| Hermes Agent | Orchestrator otomasi (Nous Research + Gemini Flash Lite) |
| Postiz v2.11.3 | Social media scheduler, self-hosted di WSL2 |
| Pinterest API v5 | Standard tier (App ID: 1592056) |
| Windows Task Scheduler | Trigger WSL2 + Hermes per sesi |

### Jadwal Posting (WIB)

| Sesi | Jam | Pin |
|------|-----|-----|
| Sesi 1 | 09:30 | 2 pin |
| Sesi 2 | 12:30 | 2 pin |
| Sesi 3 | 18:00 | 2 pin |

- Total target: ~6 pin/hari, 7 hari seminggu
- WSL2 start 15 menit sebelum sesi, shutdown setelah ~30 menit
- PC mati = sesi terlewat; folder `READY_` tetap ada, diambil sesi berikutnya
- Pilih 2 pin per sesi dengan canvas ratio berbeda jika tersedia

### SEO Keywords

- Dikelola via `seo_keywords.json` sebagai single source of truth
- Update otomatis setiap Senin 09:00 WIB oleh Hermes via pytrends + Pinterest Trends
- Push ke GitHub → trigger Streamlit Cloud auto-redeploy

---

## 12. Postiz Setup

Self-hosted di WSL2 Docker Engine (bukan Docker Desktop — hemat RAM).

**Cara start:**
```bash
# Dari PowerShell Windows:
wsl
cd /opt/postiz && docker compose up -d
```

**URL akses:** `http://localhost:4007` (jangan pakai IP WSL — menyebabkan login infinite loading)

**Container:**
- `postiz` — app (port 4007→5000)
- `postiz-postgres` — PostgreSQL 17
- `postiz-redis` — Redis 7.2

**Konfigurasi penting di `docker-compose.yml`:**
- `MAIN_URL`, `FRONTEND_URL`, `NEXT_PUBLIC_BACKEND_URL` → `http://localhost:4007`
- `PINTEREST_CLIENT_ID`: `1592056`
- Versi terkunci: v2.11.3 (v2.12+ ditolak — overhead Temporal/Elasticsearch > 8GB RAM)

---

## 13. Pinterest Agent

File: `G:\HERMES\Pinterest Hasflo\pinterest_agent.py`

**Status:** rancangan selesai, belum dikoding (Oktober 2026). Semua credentials dan dependencies sudah siap.

### Alur Agent

1. Load credentials dari `.env`
2. Cek & refresh Pinterest access token jika expired → simpan ke `pinterest_token.json`
3. Fetch list folder dari Dropbox root → filter prefix `READY_`
4. Pilih max 2 folder random, prioritas canvas ratio berbeda
5. Per folder:
   - Download `ready_pin/deskripsi.txt` → parse 4 baris
   - Download semua media dari `ready_pin/`
   - Resolve Board ID + Section ID via Pinterest API
   - Upload tiap gambar ke Pinterest media endpoint → dapat `media_id`
   - POST carousel pin ke `/v5/pins`
   - Sukses → pindah `ready_pin/` ke subfolder `DONE/`
   - Gagal → folder tetap `READY_`, log error, retry sesi berikutnya
6. Log ke `agent_log.txt`

### Urutan Slide Carousel

1. `ready_pin/slides/slide1.jpg` — hasil collage GPT (slide utama)
2. `ready_pin/image1.jpg`
3. `ready_pin/image2.jpg`
4. `ready_pin/image3.jpg`
5. `ready_pin/image4.jpg` *(opsional, max 5 slide total)*

### Mitigasi Error

| Kondisi | Perilaku |
|---------|---------|
| Tidak ada folder `READY_` | Log "No pins ready" → exit normal |
| Posting gagal | Folder tetap `READY_` → retry otomatis sesi berikutnya |
| Token expired | Auto-refresh via refresh_token; gagal → log + exit |

### Dependencies

```
Python 3.14.5 (Windows system, C:\Users\HFS\AppData\Local\Programs\Python\Python314\)
requests
python-dotenv
```

Tidak butuh conda env — Python system Windows langsung.

---

## 14. Catatan Teknis

### Streamlit

- **Set session_state untuk key widget setelah widget ter-instantiate** → `StreamlitAPIException`. Solusi: strip/transform nilai saat diambil downstream, bukan saat input.
- **Path model** wajib pakai `os.path.dirname(os.path.abspath(__file__))` — Streamlit Cloud gagal resolve relative path.
- Ekstensi file model harus case-insensitive (`.PNG`/`.png`) karena filesystem Linux case-sensitive.

### Data

- CSV output (processor.py) wajib `lineterminator="\r\n"` (CRLF) — jangan buka di Excel sebelum upload ke Pinterest bulk tool.
- Shopee CDN `.webp` URL diterima langsung oleh Pinterest.
- Shopee link cleaning: strip query string dari `?` onward + strip trailing dot.

### Dropbox

- Access token lifetime: ~4 jam. Di-refresh fresh tiap sesi upload.
- Folder rename setelah `ready_pin/` terupload: `{folder}` → `READY_{folder}`.
- Setelah agent posting sukses: `ready_pin/` dipindah ke subfolder `DONE/` (bukan rename folder parent lagi).

### Pinterest API

- Tier: Standard (App ID: 1592056), approved Oktober 2026.
- Generated Access Token dari dashboard Pinterest: expire 24 jam (testing only).
- App Secret Key via Postiz: OAuth refresh otomatis, pipeline tidak perlu intervensi manual.
- `refresh_token_expires_at`: ~60 hari dari Oktober 2026 → perlu diperbarui sekitar Desember 2026.
- Board ID di-resolve dari nama string via `GET /v5/boards` per sesi (tidak di-cache ke file).

### Ruled Out

- Gemini image generation: zero free quota pada image-output models → tidak feasible.
- VPS: ditolak — constraint tidak ada kartu kredit untuk cloud service.
- Postiz v2.12+: overhead Temporal/Elasticsearch melebihi 8GB RAM.
- Amazon Associates: geographic mismatch, butuh rekening US/India.

# ============================================================
# HASFLO PINTEREST — _credentials.py
# Baca credentials dari st.secrets (Streamlit Cloud).
# Lokal: isi .streamlit/secrets.toml
# ============================================================

import streamlit as st

AI_ENABLED            = True  # selalu aktif
AI_API_KEY            = st.secrets["AI_API_KEY"]
AI_MODEL              = st.secrets.get("AI_MODEL", "gemini-3.1-flash-lite")
DROPBOX_APP_KEY       = st.secrets["DROPBOX_APP_KEY"]
DROPBOX_APP_SECRET    = st.secrets["DROPBOX_APP_SECRET"]
DROPBOX_REFRESH_TOKEN = st.secrets["DROPBOX_REFRESH_TOKEN"]
DROPBOX_FOLDER        = st.secrets.get("DROPBOX_FOLDER", "/HASflo")

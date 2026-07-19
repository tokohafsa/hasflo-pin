# ============================================================
# HASFLO PINTEREST — _credentials.py
# Helper: baca credentials dari st.secrets (cloud) atau
# secrets.py (lokal). Di-import oleh app.py, processor.py,
# title_desc_generator.py.
# File ini BOLEH masuk repo — tidak berisi nilai sensitif.
# ============================================================

def _get(key: str, default=None):
    """
    Coba baca dari st.secrets dulu (Streamlit Cloud).
    Fallback ke secrets.py kalau tidak ada / bukan konteks Streamlit.
    """
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val is not None:
            return val
    except Exception:
        pass

    try:
        import secrets as _s
        return getattr(_s, key, default)
    except Exception:
        pass

    return default


AI_ENABLED            = _get(True, False)
AI_API_KEY            = _get("AI_API_KEY", "")
DROPBOX_APP_KEY       = _get("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET    = _get("DROPBOX_APP_SECRET", "")
DROPBOX_REFRESH_TOKEN = _get("DROPBOX_REFRESH_TOKEN", "")

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
    Fallback ke secrets.py (lokal) via importlib untuk menghindari
    konflik dengan Python built-in module 'secrets'.
    """
    # 1. Coba st.secrets (Streamlit Cloud)
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val is not None:
            return val
    except Exception:
        pass

    # 2. Fallback ke secrets.py lokal via importlib
    # (menghindari konflik dengan stdlib 'secrets' module)
    try:
        import importlib.util, os
        _path = os.path.join(os.path.dirname(__file__), "secrets.py")
        _spec = importlib.util.spec_from_file_location("_local_secrets", _path)
        _mod  = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        val = getattr(_mod, key, None)
        if val is not None:
            return val
    except Exception:
        pass

    return default


AI_ENABLED            = _get("AI_ENABLED", True)
AI_API_KEY            = _get("AI_API_KEY", "")
AI_MODEL              = _get("AI_MODEL", "gemini-3.1-flash-lite")
DROPBOX_APP_KEY       = _get("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET    = _get("DROPBOX_APP_SECRET", "")
DROPBOX_REFRESH_TOKEN = _get("DROPBOX_REFRESH_TOKEN", "")
DROPBOX_FOLDER        = _get("DROPBOX_FOLDER", "/HASflo")

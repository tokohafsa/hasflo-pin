# ============================================================
# HASFLO PINTEREST - DROPBOX CLIENT
# Upload folder ke Dropbox via OAuth2 (refresh token)
# ============================================================

import os
import requests


# ============================================================
# TOKEN REFRESH
# ============================================================

def _get_access_token(app_key: str, app_secret: str, refresh_token: str) -> str:
    """
    Tukar refresh token dengan access token baru (short-lived, ~4 jam).
    Dipanggil setiap kali upload — tidak perlu simpan access token ke disk.
    """
    resp = requests.post(
        "https://api.dropbox.com/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": app_key,
            "client_secret": app_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        raise ValueError(f"Dropbox token refresh gagal: {data}")
    return data["access_token"]


# ============================================================
# UPLOAD FILE TUNGGAL
# ============================================================

def upload_file(
    local_path: str,
    dropbox_path: str,
    access_token: str,
    overwrite: bool = True,
) -> dict:
    """
    Upload satu file ke Dropbox.
    
    local_path    : path file lokal yang akan diupload
    dropbox_path  : path tujuan di Dropbox (harus mulai dari /)
    access_token  : short-lived access token dari _get_access_token()
    overwrite     : True = timpa kalau sudah ada
    """
    mode = "overwrite" if overwrite else "add"

    with open(local_path, "rb") as f:
        data = f.read()

    resp = requests.post(
        "https://content.dropboxapi.com/2/files/upload",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Dropbox-API-Arg": __import__("json").dumps({
                "path": dropbox_path,
                "mode": mode,
                "autorename": not overwrite,
                "mute": True,
            }),
            "Content-Type": "application/octet-stream",
        },
        data=data,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# UPLOAD IN-MEMORY BYTES (untuk ZIP yang belum disimpan ke disk)
# ============================================================

def upload_bytes(
    file_bytes: bytes,
    dropbox_path: str,
    access_token: str,
    overwrite: bool = True,
) -> dict:
    """
    Upload bytes langsung ke Dropbox (tanpa perlu simpan ke disk dulu).
    Cocok untuk ZIP yang dibuild di memory (io.BytesIO).
    """
    mode = "overwrite" if overwrite else "add"

    resp = requests.post(
        "https://content.dropboxapi.com/2/files/upload",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Dropbox-API-Arg": __import__("json").dumps({
                "path": dropbox_path,
                "mode": mode,
                "autorename": not overwrite,
                "mute": True,
            }),
            "Content-Type": "application/octet-stream",
        },
        data=file_bytes,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# UPLOAD FOLDER LOKAL (rekursif)
# ============================================================

def upload_folder(
    local_folder: str,
    dropbox_root: str,
    access_token: str,
    overwrite: bool = True,
    progress_callback=None,
) -> list:
    """
    Upload seluruh isi folder lokal ke Dropbox secara rekursif.

    local_folder      : path folder lokal (contoh: "output/[2x3]judulXYZ_20260719")
    dropbox_root      : path Dropbox tujuan (contoh: "/HASflo/[2x3]judulXYZ_20260719")
    access_token      : short-lived access token
    overwrite         : timpa file yang sudah ada
    progress_callback : opsional, fn(current, total, filename) untuk update progress bar

    Return: list of dict hasil upload per file
    """
    results = []
    all_files = []

    # Kumpulkan semua file dulu untuk progress
    for dirpath, _, filenames in os.walk(local_folder):
        for filename in filenames:
            all_files.append(os.path.join(dirpath, filename))

    total = len(all_files)

    for idx, local_path in enumerate(all_files, start=1):
        # Derive path Dropbox relatif dari local_folder
        rel = os.path.relpath(local_path, local_folder)
        rel_posix = rel.replace("\\", "/")  # Windows-safe
        dropbox_path = f"{dropbox_root.rstrip('/')}/{rel_posix}"

        try:
            result = upload_file(local_path, dropbox_path, access_token, overwrite)
            results.append({"path": dropbox_path, "status": "ok", "result": result})
        except Exception as e:
            results.append({"path": dropbox_path, "status": "error", "error": str(e)})

        if progress_callback:
            progress_callback(idx, total, os.path.basename(local_path))

    return results


# ============================================================
# RENAME FOLDER DI DROPBOX (untuk _DONE marker)
# ============================================================

def rename_folder(
    dropbox_path: str,
    new_dropbox_path: str,
    access_token: str,
) -> dict:
    """
    Rename / move folder di Dropbox.
    Dipakai agent untuk rename ready_pin/ → ready_pin_DONE/ setelah posting.

    dropbox_path     : path lama (contoh: "/HASflo/judulXYZ/ready_pin")
    new_dropbox_path : path baru (contoh: "/HASflo/judulXYZ/ready_pin_DONE")
    """
    resp = requests.post(
        "https://api.dropbox.com/2/files/move_v2",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "from_path": dropbox_path,
            "to_path": new_dropbox_path,
            "allow_shared_folder": False,
            "autorename": False,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# LIST SUBFOLDER (untuk agent poll)
# ============================================================

def list_subfolders(
    dropbox_root: str,
    access_token: str,
) -> list:
    """
    List semua subfolder langsung di bawah dropbox_root.
    Dipakai agent untuk poll /HASflo/ dan temukan folder yang belum _DONE.

    Return: list of str (path Dropbox tiap subfolder)
    """
    resp = requests.post(
        "https://api.dropbox.com/2/files/list_folder",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "path": dropbox_root.rstrip("/") or "",
            "recursive": False,
            "include_deleted": False,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        entry["path_display"]
        for entry in data.get("entries", [])
        if entry[".tag"] == "folder"
    ]


# ============================================================
# HIGH-LEVEL: upload ZIP folder dari app.py
# ============================================================

def upload_zip_folder_to_dropbox(
    zip_folder_path: str,
    folder_name: str,
    app_key: str,
    app_secret: str,
    refresh_token: str,
    dropbox_root: str = "/HASflo",
    progress_callback=None,
) -> dict:
    """
    Entry point utama dari app.py di Step 7.

    zip_folder_path : path lokal folder yang sudah diekstrak / folder sumber
                      (bahan_prompt/ dan ready_pin/ ada di dalamnya)
    folder_name     : nama folder tujuan di Dropbox (contoh: "[2x3]judulXYZ_20260719")
    app_key / app_secret / refresh_token : dari config.py
    dropbox_root    : root folder di Dropbox, default "/HASflo"

    Return: dict {"success": bool, "errors": list, "dropbox_path": str}
    """
    dropbox_dest = f"{dropbox_root.rstrip('/')}/{folder_name}"

    try:
        access_token = _get_access_token(app_key, app_secret, refresh_token)
    except Exception as e:
        return {"success": False, "errors": [f"Token refresh gagal: {e}"], "dropbox_path": dropbox_dest}

    results = upload_folder(
        local_folder=zip_folder_path,
        dropbox_root=dropbox_dest,
        access_token=access_token,
        overwrite=True,
        progress_callback=progress_callback,
    )

    errors = [r["path"] + ": " + r.get("error", "") for r in results if r["status"] == "error"]

    return {
        "success": len(errors) == 0,
        "errors": errors,
        "dropbox_path": dropbox_dest,
        "uploaded": len([r for r in results if r["status"] == "ok"]),
        "total": len(results),
    }

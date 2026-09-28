"""Subida a Google Drive con OAuth (refresh token) y permiso mínimo `drive.file`.

Con `drive.file` la app solo ve las carpetas/archivos que ella misma crea, por eso
crea su propia carpeta raíz ("YouTube Automático") en tu Drive.
"""
from __future__ import annotations

import datetime as dt
import json
import mimetypes
import os
import re
from pathlib import Path

import requests

from .util import log, retry

API = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER = "application/vnd.google-apps.folder"


class Drive:
    def __init__(self) -> None:
        r = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": os.environ["GDRIVE_CLIENT_ID"],
                "client_secret": os.environ["GDRIVE_CLIENT_SECRET"],
                "refresh_token": os.environ["GDRIVE_REFRESH_TOKEN"],
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"No se pudo renovar el token de Drive: {r.text}")
        self.h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    @staticmethod
    def configured() -> bool:
        return all(os.environ.get(k) for k in ("GDRIVE_CLIENT_ID", "GDRIVE_CLIENT_SECRET", "GDRIVE_REFRESH_TOKEN"))

    def folder(self, name: str, parent: str | None = None) -> str:
        safe = name.replace("'", "\\'")
        q = f"name = '{safe}' and mimeType = '{FOLDER}' and trashed = false"
        if parent:
            q += f" and '{parent}' in parents"
        r = requests.get(API, headers=self.h, params={"q": q, "fields": "files(id)"}, timeout=30)
        r.raise_for_status()
        if files := r.json()["files"]:
            return files[0]["id"]
        meta = {"name": name, "mimeType": FOLDER, **({"parents": [parent]} if parent else {})}
        r = requests.post(API, headers=self.h, json=meta, timeout=30)
        r.raise_for_status()
        return r.json()["id"]

    def upload(self, path: Path, parent: str) -> str:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        size = path.stat().st_size

        def _do() -> str:
            init = requests.post(
                UPLOAD,
                params={"uploadType": "resumable"},
                headers={**self.h, "Content-Type": "application/json; charset=UTF-8",
                         "X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(size)},
                data=json.dumps({"name": path.name, "parents": [parent]}),
                timeout=30,
            )
            init.raise_for_status()
            with open(path, "rb") as f:
                r = requests.put(init.headers["Location"], data=f,
                                 headers={"Content-Type": mime, "Content-Length": str(size)}, timeout=1800)
            r.raise_for_status()
            return r.json()["id"]

        return retry(_do, tries=3, what=f"subida de {path.name}")

    def cleanup(self, root: str, keep_days: int) -> None:
        """Borra definitivamente las carpetas de fecha (AAAA-MM-DD) más antiguas que keep_days."""
        limit = (dt.date.today() - dt.timedelta(days=keep_days)).isoformat()
        q = f"'{root}' in parents and mimeType = '{FOLDER}' and trashed = false"
        r = requests.get(API, headers=self.h, params={"q": q, "fields": "files(id,name)", "pageSize": 1000}, timeout=30)
        r.raise_for_status()
        for f in r.json()["files"]:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f["name"]) and f["name"] < limit:
                requests.delete(f"{API}/{f['id']}", headers=self.h, timeout=30).raise_for_status()
                log(f"  🗑 Drive: borrada la carpeta antigua {f['name']}")


def upload_folder(local: Path, remote_path: list[str], keep_days: int = 7) -> None:
    drive = Drive()
    root = drive.folder("YouTube Automático")
    try:
        drive.cleanup(root, keep_days)
    except Exception as e:  # noqa: BLE001 — la limpieza nunca debe impedir la subida
        log(f"  ⚠ limpieza de Drive: {e}")
    parent = root
    for part in remote_path:
        parent = drive.folder(part, parent)
    for f in sorted(local.iterdir()):
        if f.is_file():
            drive.upload(f, parent)
            log(f"  ☁ Drive: {'/'.join(remote_path)}/{f.name}")

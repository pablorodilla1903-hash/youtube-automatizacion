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

    def list_files(self, parent: str, with_size: bool = False) -> dict:
        r = requests.get(API, headers=self.h, timeout=30, params={
            "q": f"'{parent}' in parents and trashed = false", "fields": "files(id,name,size,mimeType)", "pageSize": 1000})
        r.raise_for_status()
        files = r.json()["files"]
        if with_size:  # las carpetas no tienen tamaño: nunca se borran por sincronizar
            return {f["name"]: (f["id"], int(f["size"]) if "size" in f else None) for f in files}
        return {f["name"]: f["id"] for f in files}

    def cleanup(self, parent: str, keep_days: int) -> None:
        """Borra definitivamente las carpetas de vídeos (que empiezan por AAAA-MM-DD) más antiguas que keep_days."""
        limit = (dt.date.today() - dt.timedelta(days=keep_days)).isoformat()
        for name, fid in self.list_files(parent).items():
            if re.match(r"\d{4}-\d{2}-\d{2}", name) and name[:10] < limit:
                requests.delete(f"{API}/{fid}", headers=self.h, timeout=30).raise_for_status()
                log(f"  🗑 Drive: borrada la carpeta antigua {name}")


ROOT_FOLDER = "YouTube Automático"
BRAND_FOLDER = "0_Marca y textos"


def upload_folder(local: Path, remote_path: list[str], keep_days: int | None = None, skip_existing: bool = False,
                  sync: bool = False) -> None:
    """Sube los archivos de `local` a YouTube Automático/<remote_path...>.

    keep_days: borra antes las carpetas de vídeos antiguas del penúltimo nivel (la carpeta del canal).
    skip_existing: no vuelve a subir archivos que ya estén (por nombre).
    sync: además, sustituye los archivos que cambiaron de tamaño y borra los que ya no existen en local.
    """
    drive = Drive()
    parent = drive.folder(ROOT_FOLDER)
    for i, part in enumerate(remote_path):
        parent = drive.folder(part, parent)
        if keep_days is not None and i == len(remote_path) - 2:
            try:
                drive.cleanup(parent, keep_days)
            except Exception as e:  # noqa: BLE001 — la limpieza nunca debe impedir la subida
                log(f"  ⚠ limpieza de Drive: {e}")
    existing = drive.list_files(parent, with_size=sync) if (skip_existing or sync) else {}
    local_files = {f.name: f for f in local.iterdir() if f.is_file()}
    if sync:
        for name, (fid, size) in existing.items():
            lf = local_files.get(name)
            if size is not None and (lf is None or lf.stat().st_size != size):
                requests.delete(f"{API}/{fid}", headers=drive.h, timeout=30).raise_for_status()
                log(f"  🗑 Drive: {'/'.join(remote_path)}/{name}")
        existing = {k: v for k, v in existing.items() if k in local_files and v[1] == local_files[k].stat().st_size}
    for name, f in sorted(local_files.items()):
        if name not in existing:
            drive.upload(f, parent)
            log(f"  ☁ Drive: {'/'.join(remote_path)}/{name}")

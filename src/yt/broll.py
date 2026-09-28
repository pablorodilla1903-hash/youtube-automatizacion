"""Vídeos de archivo gratuitos de Pexels (licencia libre, uso comercial permitido)."""
from __future__ import annotations

import os
import random
from pathlib import Path

import requests

from .util import log

CACHE = Path("cache/pexels")


class BrollPicker:
    def __init__(self, vertical: bool, generic: list[str]):
        self.key = os.environ.get("PEXELS_API_KEY", "")
        self.vertical = vertical
        self.generic = generic
        self.used: set[int] = set()
        self._search_cache: dict[str, list[dict]] = {}
        CACHE.mkdir(parents=True, exist_ok=True)

    def _search(self, query: str) -> list[dict]:
        if query in self._search_cache:
            return self._search_cache[query]
        try:
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": self.key},
                params={
                    "query": query,
                    "per_page": 15,
                    "orientation": "portrait" if self.vertical else "landscape",
                    "size": "medium",
                },
                timeout=30,
            )
            r.raise_for_status()
            videos = r.json().get("videos", [])
        except Exception as e:  # noqa: BLE001
            log(f"  ⚠ Pexels '{query}': {e}")
            videos = []
        self._search_cache[query] = videos
        return videos

    def _best_file(self, video: dict) -> dict | None:
        files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
        if not files:
            return None
        target = 1080 if self.vertical else 1920
        # El más pequeño que cubra la resolución objetivo (evita descargar 4K); si no hay, el más grande.
        good = [f for f in files if f["width"] >= target]
        return min(good, key=lambda f: f["width"]) if good else max(files, key=lambda f: f["width"])

    def _download(self, video: dict) -> Path | None:
        f = self._best_file(video)
        if not f:
            return None
        path = CACHE / f"{video['id']}_{f['width']}x{f['height']}.mp4"
        if path.exists() and path.stat().st_size > 0:
            return path
        try:
            with requests.get(f["link"], stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(path, "wb") as out:
                    for chunk in r.iter_content(1 << 20):
                        out.write(chunk)
            return path
        except Exception as e:  # noqa: BLE001
            log(f"  ⚠ descarga Pexels {video['id']}: {e}")
            path.unlink(missing_ok=True)
            return None

    def pick(self, queries: list[str], n: int) -> list[Path]:
        """Devuelve hasta n clips distintos para las búsquedas dadas (sin repetir en el vídeo)."""
        if not self.key:
            return []
        out: list[Path] = []
        candidates: list[dict] = []
        simplified = [" ".join(q.split()[:2]) for q in queries]
        for q in [*queries, *simplified, random.choice(self.generic)]:
            candidates += [v for v in self._search(q) if v["id"] not in self.used and v.get("duration", 0) >= 3]
            if len({v["id"] for v in candidates}) >= n:
                break
        seen: set[int] = set()
        for v in candidates:
            if len(out) >= n:
                break
            if v["id"] in seen:
                continue
            seen.add(v["id"])
            p = self._download(v)
            if p:
                self.used.add(v["id"])
                out.append(p)
        return out

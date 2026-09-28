"""Utilidades compartidas: ffmpeg, duraciones, logging."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


@lru_cache(maxsize=None)
def ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(args: list[str]) -> None:
    cmd = [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", *args]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr[-3000:])
        raise RuntimeError(f"ffmpeg falló: {' '.join(cmd[:12])}...")


def media_duration(path: Path) -> float:
    """Duración en segundos (decodificando, preciso también para mp3)."""
    res = subprocess.run(
        [ffmpeg_bin(), "-hide_banner", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    times = re.findall(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr)
    if not times:
        m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr)
        if not m:
            raise RuntimeError(f"No se pudo leer la duración de {path}")
        times = [m.groups()]
    h, m_, s = times[-1]
    return int(h) * 3600 + int(m_) * 60 + float(s)


def retry(fn, tries: int = 3, wait: float = 5.0, what: str = "operación"):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            log(f"  ⚠ {what} falló (intento {i + 1}/{tries}): {e}")
            time.sleep(wait * (i + 1))
    raise RuntimeError(f"{what} falló tras {tries} intentos") from last


FONT_CANDIDATES = [
    "fonts/Anton-Regular.ttf",
    str(Path.home() / ".local/share/fonts/Anton-Regular.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


def bold_font() -> str:
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return f
    raise FileNotFoundError("No se encontró ninguna fuente en negrita")

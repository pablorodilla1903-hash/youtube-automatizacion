"""Locución gratuita.

- "edge"   (por defecto): voces neuronales de Microsoft Edge vía edge-tts. Gratis, sin cuenta ni tarjeta.
- "google" (opcional):    Google Cloud Text-to-Speech, voces Chirp 3 HD. Tiene cuota gratuita mensual,
                          pero exige cuenta de facturación con tarjeta. Requiere GOOGLE_TTS_API_KEY.
- "offline" (pruebas):    silencio con tiempos estimados, para probar el montaje sin red.
"""
from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path

import requests

from .util import log, media_duration, retry, run_ffmpeg

Word = tuple[float, float, str]  # (inicio, fin, texto)


def _estimate_words(text: str, duration: float, lead: float = 0.05) -> list[Word]:
    """Reparte la duración entre palabras en proporción a su longitud."""
    words = text.split()
    total = sum(len(w) + 1 for w in words) or 1
    t, out = lead, []
    usable = max(duration - lead * 2, 0.1)
    for w in words:
        d = usable * (len(w) + 1) / total
        out.append((t, t + d, w))
        t += d
    return out


def _to_wav(src: Path, dst: Path) -> None:
    run_ffmpeg(["-i", str(src), "-ar", "44100", "-ac", "1", str(dst)])


async def _edge_async(text: str, voice: str, rate: str, mp3: Path) -> list[Word]:
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words: list[Word] = []
    with open(mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append((start, start + chunk["duration"] / 1e7, chunk["text"]))
    if mp3.stat().st_size == 0:
        raise RuntimeError("edge-tts devolvió audio vacío")
    return words


def _edge(text: str, cfg: dict, out_wav: Path) -> list[Word]:
    mp3 = out_wav.with_suffix(".mp3")
    words = asyncio.run(_edge_async(text, cfg["voz"], cfg.get("velocidad_voz", "+0%"), mp3))
    _to_wav(mp3, out_wav)
    if not words:
        words = _estimate_words(text, media_duration(out_wav))
    return words


def _google(text: str, cfg: dict, out_wav: Path) -> list[Word]:
    voice = cfg.get("voz_google") or ("es-US-Chirp3-HD-Charon" if cfg["idioma"] == "es" else "en-US-Chirp3-HD-Charon")
    r = requests.post(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        params={"key": os.environ["GOOGLE_TTS_API_KEY"]},
        json={
            "input": {"text": text},
            "voice": {"languageCode": "-".join(voice.split("-")[:2]), "name": voice},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 44100},
        },
        timeout=120,
    )
    r.raise_for_status()
    raw = out_wav.with_suffix(".raw.wav")
    raw.write_bytes(base64.b64decode(r.json()["audioContent"]))
    _to_wav(raw, out_wav)
    return _estimate_words(text, media_duration(out_wav))


def _offline(text: str, cfg: dict, out_wav: Path) -> list[Word]:
    duration = max(len(text.split()) / 2.6, 1.0)  # ≈156 palabras/minuto
    run_ffmpeg(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{duration:.3f}", str(out_wav)])
    return _estimate_words(text, duration)


PROVIDERS = {"edge": _edge, "google": _google, "offline": _offline}


def synthesize(text: str, cfg: dict, out_wav: Path) -> tuple[float, list[Word]]:
    provider = os.environ.get("TTS_PROVIDER", "edge")
    if provider == "google" and not os.environ.get("GOOGLE_TTS_API_KEY"):
        provider = "edge"
    order = [provider] + (["edge"] if provider == "google" else [])
    for i, name in enumerate(order):
        try:
            words = retry(lambda: PROVIDERS[name](text, cfg, out_wav), tries=3, what=f"voz {name}")
            return media_duration(out_wav), words
        except Exception:
            if i == len(order) - 1:
                raise
            log(f"  ⚠ voz {name} falló, usando la siguiente")
    raise AssertionError("unreachable")

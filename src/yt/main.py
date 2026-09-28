"""Genera el vídeo del día (y el Short) para cada canal activo.

Uso:
    python -m yt.main                 # todos los canales activos
    python -m yt.main --canal es      # solo uno
    python -m yt.main --offline       # prueba sin red (guion de ejemplo, voz muda, fondos)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import shutil
import sys
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from . import content, drive
from .broll import BrollPicker
from .render import Segment, render
from .thumbnail import make_thumbnail
from .tts import synthesize
from .util import log

ROOT = Path(__file__).resolve().parents[2]


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def _voice_segments(raw: list[dict], cfg: dict, workdir: Path, prefix: str) -> list[Segment]:
    workdir.mkdir(parents=True, exist_ok=True)
    out = []
    for i, s in enumerate(raw):
        wav = workdir / f"{prefix}_voz_{i:03d}.wav"
        dur, words = synthesize(s["text"], cfg, wav)
        out.append(Segment(s["text"], s.get("broll", []), wav, dur, words))
    return out


def _pick_music() -> Path | None:
    tracks = sorted((ROOT / "assets/musica").glob("*.mp3"))
    return random.choice(tracks) if tracks else None


def _fmt_tags(tags: list[str]) -> str:
    out, total = [], 0
    for t in tags:
        t = t.replace(",", " ").strip()
        if t and total + len(t) + 1 <= 480:  # límite de YouTube: 500 caracteres
            out.append(t)
            total += len(t) + 1
    return ", ".join(out)


def _write_readme(pkg: dict, cfg: dict, date: dt.date, tz: str, out_dir: Path, minutes: float) -> None:
    short = pkg.get("short") or {}
    hashtags = " ".join(pkg.get("hashtags", []))
    lines = [
        f"CANAL: {cfg['nombre']}   ·   FECHA: {date.isoformat()}   ·   DURACIÓN: {minutes:.1f} min",
        "",
        f"⏰ PROGRAMAR PUBLICACIÓN DEL VÍDEO: {cfg['publicar']['video']} (hora {tz})",
        f"⏰ PROGRAMAR PUBLICACIÓN DEL SHORT: {cfg['publicar']['short']} (hora {tz})" if short else "",
        "",
        "════════ VÍDEO LARGO (1_VIDEO.mp4) ════════",
        "TÍTULO:", pkg["title"], "",
        "TÍTULOS ALTERNATIVOS (para 'Probar y comparar' de YouTube):",
        *[f"  - {t}" for t in pkg.get("alt_titles", [])], "",
        "DESCRIPCIÓN:", pkg["description"].strip(), "", hashtags, "",
        "ETIQUETAS (pegar en 'Etiquetas'):", _fmt_tags(pkg.get("tags", [])), "",
        "MINIATURA: 2_MINIATURA.jpg      SUBTÍTULOS: 3_SUBTITULOS.srt (Subtítulos → Subir archivo → Con tiempos)",
        "",
        "COMENTARIO PARA FIJAR:", pkg.get("pinned_comment", ""), "",
    ]
    if short:
        lines += ["════════ SHORT (4_SHORT.mp4) ════════", "TÍTULO:", short.get("title", ""), "",
                  "DESCRIPCIÓN:", short.get("description", ""), ""]
    if pkg.get("sources_to_check"):
        lines += ["════════ ✅ REVISA ESTOS DATOS ANTES DE PUBLICAR (2 minutos) ════════",
                  *[f"  - {s}" for s in pkg["sources_to_check"]], ""]
    lines += ["════════ GUION COMPLETO ════════", *[s["text"] + "\n" for s in pkg["segments"]]]
    (out_dir / "LEEME_SUBIR.txt").write_text("\n".join(l for l in lines if l is not None), "utf-8")


def run_channel(channel_id: str, cfg: dict, date: dt.date, tz: str, offline: bool, keep_days: int = 7) -> Path:
    log(f"══ Canal {cfg['nombre']} ({channel_id}) ══")
    out_dir = ROOT / "salida" / date.isoformat() / _slug(cfg["nombre"])
    work = ROOT / "cache" / "trabajo" / channel_id
    shutil.rmtree(work, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    log("1/5 Tema y guion con IA…")
    if offline:
        pkg = json.loads((ROOT / "tests/paquete_ejemplo.json").read_text("utf-8"))
    else:
        pkg = content.generate_package(channel_id, cfg)
    (out_dir / "guion.json").write_text(json.dumps(pkg, ensure_ascii=False, indent=2), "utf-8")
    log(f"  Título: {pkg['title']}")

    log("2/5 Locución…")
    segs = _voice_segments(pkg["segments"], cfg, work / "voz", "largo")

    log("3/5 Montaje del vídeo largo…")
    music = _pick_music()
    video = out_dir / "1_VIDEO.mp4"
    seconds = render(segs, work / "largo", video, vertical=False,
                     picker=BrollPicker(False, cfg["busqueda_generica"]), music=music,
                     music_volume=float(cfg.get("musica_volumen", 0)), burn_subs=False,
                     srt_out=out_dir / "3_SUBTITULOS.srt")

    log("4/5 Miniatura…")
    make_thumbnail(video, pkg["thumbnail_text"], pkg.get("thumbnail_highlight", ""), out_dir / "2_MINIATURA.jpg")

    if cfg.get("short") and pkg.get("short"):
        log("5/5 Short vertical…")
        ssegs = _voice_segments(pkg["short"]["segments"], cfg, work / "voz", "short")
        render(ssegs, work / "short", out_dir / "4_SHORT.mp4", vertical=True,
               picker=BrollPicker(True, cfg["busqueda_generica"]), music=music,
               music_volume=float(cfg.get("musica_volumen", 0)), burn_subs=True, srt_out=None)

    _write_readme(pkg, cfg, date, tz, out_dir, seconds / 60)

    if not offline:
        history = content.load_history(channel_id)
        history.append({"date": date.isoformat(), "topic": pkg.get("topic", ""), "title": pkg["title"]})
        content.save_history(channel_id, history)

    if drive.Drive.configured() and not offline:
        log("Subiendo a Google Drive…")
        drive.upload_folder(out_dir, [date.isoformat(), cfg["nombre"]], int(keep_days))
    log(f"✔ {cfg['nombre']}: {seconds / 60:.1f} min → {out_dir}")
    return out_dir


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canal", help="id del canal (en, es…)")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    os.chdir(ROOT)
    if args.offline:
        os.environ["TTS_PROVIDER"] = "offline"
        os.environ.pop("PEXELS_API_KEY", None)

    conf = yaml.safe_load((ROOT / "config/canales.yaml").read_text("utf-8"))
    tz = conf.get("zona_horaria", "Europe/Madrid")
    date = dt.datetime.now(ZoneInfo(tz)).date()
    channels = {k: v for k, v in conf["canales"].items() if v.get("activo", True)}
    if args.canal:
        channels = {args.canal: conf["canales"][args.canal]}

    failed = []
    for cid, cfg in channels.items():
        try:
            run_channel(cid, cfg, date, tz, args.offline, conf.get("drive_dias_guardar", 7))
        except Exception:  # noqa: BLE001 — un canal roto no debe tumbar al otro
            traceback.print_exc()
            failed.append(cid)
    if failed:
        log(f"✘ Fallaron: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

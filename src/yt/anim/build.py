"""Convierte un guion animado (script.json) en vídeo terminado: voz, escenas 2D, subtítulos, miniaturas y ficha.

Uso:
    python -m yt.anim.build guiones/ingenieria/001_cables_submarinos.json
    python -m yt.anim.build <guion> --preview 3     # solo las 3 primeras escenas (prueba rápida)
    python -m yt.anim.build <guion> --short          # además, el Short vertical
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

from ..util import ffmpeg_bin, log, media_duration, run_ffmpeg
from . import scenes as S

ROOT = Path(__file__).resolve().parents[3]
FPS = 30
PAD = 0.35  # silencio tras cada frase (respiro natural)

KOKORO_DIR = ROOT / "cache/kokoro"
KOKORO_FILES = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
GEO_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
GEO_FILES = ["ne_110m_land", "ne_50m_land", "ne_50m_admin_0_countries", "ne_50m_lakes", "ne_50m_rivers_lake_centerlines"]


# ───────────────────────── voz (Kokoro, local y gratis) ─────────────────────────

def _ensure_downloads():
    """Datos de mapas (Natural Earth)."""
    for name in GEO_FILES:
        p = ROOT / "cache/geo" / f"{name}.geojson"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(GEO_BASE + name + ".geojson", p)


def _ensure_kokoro():
    KOKORO_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in KOKORO_FILES.items():
        p = KOKORO_DIR / name
        if not p.exists():
            log(f"  descargando {name}…")
            urllib.request.urlretrieve(url, p)


_kokoro = None


def _kokoro_say(text, voice, lang, speed, wav):
    global _kokoro
    import soundfile as sf
    from kokoro_onnx import Kokoro

    if _kokoro is None:
        _ensure_kokoro()
        _kokoro = Kokoro(str(KOKORO_DIR / "kokoro-v1.0.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))
    samples, sr = _kokoro.create(text, voice=voice, speed=speed, lang=lang)
    sf.write(str(wav), samples, sr)
    return None


def _edge_say(text, voice, rate, wav):
    import asyncio

    import edge_tts

    mp3 = wav.with_suffix(".mp3")

    async def go():
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        words = []
        with open(mp3, "wb") as f:
            async for ch in comm.stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
                elif ch["type"] == "WordBoundary":
                    st = ch["offset"] / 1e7
                    words.append([ch["text"], st, st + ch["duration"] / 1e7])
        return words

    words = asyncio.run(go())
    if mp3.stat().st_size == 0:
        raise RuntimeError("edge-tts devolvió audio vacío")
    run_ffmpeg(["-i", str(mp3), "-ar", "24000", "-ac", "1", str(wav)])
    mp3.unlink()
    return words or None


class Voice:
    """Locución con caché por frase. Proveedor principal según el canal (edge/kokoro) y respaldo Kokoro."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.provider = os.environ.get("VOZ_PROVEEDOR", cfg.get("voz_proveedor", "edge"))
        self.lang = {"en": "en-us", "es": "es"}[cfg["idioma"]]

    def say(self, text: str, out: Path):
        import time as _t

        cfg = self.cfg
        order = [self.provider] + (["kokoro"] if self.provider != "kokoro" else [])
        for prov in order:
            if prov == "edge":
                ident = f"edge|{cfg.get('voz_edge')}|{cfg.get('velocidad_edge', '+0%')}"
            else:
                ident = f"kokoro|{cfg.get('voz_kokoro')}|{cfg.get('velocidad_voz', 1.0)}|{self.lang}"
            key = hashlib.sha1(f"{ident}|{text}".encode()).hexdigest()[:16]
            cached = ROOT / "cache/tts" / f"{key}.wav"
            meta = cached.with_suffix(".json")
            if not cached.exists():
                cached.parent.mkdir(parents=True, exist_ok=True)
                try:
                    for attempt in range(3):
                        try:
                            if prov == "edge":
                                words = _edge_say(text, cfg["voz_edge"], cfg.get("velocidad_edge", "+0%"), cached)
                            else:
                                words = _kokoro_say(text, cfg.get("voz_kokoro", "am_michael"), self.lang,
                                                    float(cfg.get("velocidad_voz", 1.0)), cached)
                            break
                        except Exception as e:  # noqa: BLE001
                            if attempt == 2:
                                raise
                            log(f"  ⚠ voz {prov}: {e}; reintento")
                            _t.sleep(3 * (attempt + 1))
                    meta.write_text(json.dumps(words), "utf-8")
                except Exception as e:  # noqa: BLE001
                    cached.unlink(missing_ok=True)
                    log(f"  ⚠ voz {prov} no disponible ({e}); uso la siguiente")
                    continue
            out.write_bytes(cached.read_bytes())
            words = json.loads(meta.read_text("utf-8")) if meta.exists() else None
            return media_duration(out), words
        raise RuntimeError("ninguna voz disponible")


# ───────────────────────── render de escenas ─────────────────────────

def scene_captions(text: str, speech: float, max_words: int, timings=None):
    """Subtítulos de una escena: bloques de pocas palabras con el tiempo de cada palabra
    (reales si la voz los da y cuadran con el texto; si no, estimados por longitud)."""
    words = text.split()
    if not words:
        return []
    if timings and len(timings) == len(words):
        timed = [(wd, float(a), float(b)) for wd, (_, a, b) in zip(words, timings)]
    else:
        lead = 0.08
        total = sum(len(x) + 2 for x in words)
        t, timed = lead, []
        for wd in words:
            dd = (speech - lead) * (len(wd) + 2) / total
            timed.append((wd, t, t + dd))
            t += dd
    blocks, cur = [], []
    for item in timed:
        cur.append(item)
        if len(cur) >= max_words or item[0][-1] in ".!?;:" or (item[0][-1] == "," and len(cur) >= 3):
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    out = []
    for i, b in enumerate(blocks):
        end = blocks[i + 1][0][1] if i + 1 < len(blocks) else b[-1][2] + 0.3
        out.append((b[0][1], end, b))
    return out


def _render_scene(job):
    scene, dur, th, t0, chapter, out, w, h, caps = job
    frames = max(1, round(dur * FPS))
    proc = subprocess.Popen(
        [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-f", "mp4", str(out) + ".part"],
        stdin=subprocess.PIPE,
    )
    canvas = Image.new("RGB", (w, h))
    for f in range(frames):
        t = f / FPS
        S.render_frame(canvas, scene, t, dur, th, t0 + t, chapter, caps)
        proc.stdin.write(canvas.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg falló en {out.name}")
    os.replace(str(out) + ".part", out)  # solo cuenta como hecho si se escribió entero
    return out


def _fmt_ts(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}" if sec < 3600 else f"{sec // 3600}:{sec // 60 % 60:02d}:{sec % 60:02d}"


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def _caption_chunks(text: str, start: float, dur: float, max_words: int):
    words = text.split()
    total = sum(len(w) + 1 for w in words) or 1
    chunks, cur, t = [], [], start
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w[-1] in ".,!?;:":
            L = sum(len(x) + 1 for x in cur)
            d = dur * L / total
            chunks.append((t, t + d, " ".join(cur)))
            t += d
            cur = []
    if cur:
        chunks.append((t, start + dur, " ".join(cur)))
    return chunks


# ───────────────────────── miniaturas ─────────────────────────

def _find_scene(script, typ):
    for ch in script["chapters"]:
        for sc in ch["scenes"]:
            if sc["type"] == typ:
                return sc
    return None


def _photo(prompt: str, seed: int, W: int, H: int):
    """Imagen realista generada por IA (Pollinations, gratis y sin clave). None si no está disponible."""
    import io
    import urllib.parse

    import requests

    # se pide la imagen 80 px más alta y se recorta la franja inferior (donde va la marca de agua del servicio)
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt + ", no text, no watermark")
           + f"?width={W}&height={H + 80}&seed={seed}&nologo=true&model=flux&enhance=true")
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=180)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
                img = img.resize((W, round(img.height * W / img.width)), Image.LANCZOS)
                crop_h = min(img.height, H + 80) - 80  # quita la franja inferior
                img = img.crop((0, 0, W, crop_h))
                return img.resize((W, H), Image.LANCZOS) if img.size != (W, H) else img
            log(f"  ⚠ Pollinations respondió {r.status_code}")
        except Exception as e:  # noqa: BLE001
            log(f"  ⚠ Pollinations: {e}")
        time.sleep(15 * (attempt + 1))
    return None


def photo_thumbnail(bg: Image.Image, spec: dict, th: dict) -> Image.Image:
    """Estilo documental llamativo: foto realista a toda pantalla + etiqueta pequeña + titular grande."""
    from PIL import ImageEnhance, ImageFilter

    W, H = bg.size
    img = ImageEnhance.Contrast(ImageEnhance.Color(bg).enhance(1.25)).enhance(1.1)
    # oscurecer suavemente la zona del texto
    pos = spec.get("pos", "bottom")
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for y in range(H):
        k = y / H if pos == "bottom" else 1 - y / H
        sd.line([(0, y), (W, y)], fill=int(190 * max(0.0, (k - 0.35) / 0.65) ** 1.4))
    img.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), shade.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    x = 44
    tag = spec.get("tag", "").upper()
    text = spec["text"].upper()
    hl = {w.upper() for w in spec.get("highlight", [])}
    size = 124
    while True:
        f = S.font("display", size)
        lines = S.wrap(d, text, f, W * 0.62)
        if len(lines) <= 2 or size <= 70:
            break
        size -= 6
    asc, desc = f.getmetrics()
    lh = asc + desc
    ft = S.font("display", 46)
    tag_h = 70 if tag else 0
    block_h = tag_h + len(lines) * (lh + 6)
    y = H - block_h - 40 if pos == "bottom" else 40
    if tag:
        tw = d.textlength(tag, font=ft)
        d.rectangle([x, y, x + tw + 32, y + 60], fill=th.get("accent", (255, 176, 32)))
        d.text((x + 16, y + 3), tag, font=ft, fill=(10, 10, 10))
        y += tag_h
    for line in lines:
        cx = x
        for word in line.split():
            col = th.get("accent2", (255, 210, 122)) if word.strip(".,!?%") in hl or word in hl else (255, 255, 255)
            d.text((cx, y), word, font=f, fill=col, stroke_width=max(6, size // 16), stroke_fill=(0, 0, 0))
            cx += d.textlength(word + " ", font=f)
        y += lh + 6
    return img


def thumbnails(script: dict, th: dict, out_dir: Path):
    """3 variantes 1280x720 para 'Probar y comparar': fondo, texto blanco sobre franja roja y círculo+flecha
    señalando el elemento clave (el núcleo del corte transversal)."""
    from PIL import ImageFilter

    W, H = 1280, 720
    specs = script["metadata"]["thumbnails"]
    paths = []
    for i, spec in enumerate(specs[:3]):
        if spec.get("prompt") and os.environ.get("MINIATURAS_IA", "1") == "1":
            bg = _photo(spec["prompt"], spec.get("seed", 7 + i), W, H)
            if bg is not None:
                p = out_dir / f"2 - MINIATURA {'ABC'[i]}.jpg"
                photo_thumbnail(bg, spec, th).save(p, quality=93)
                paths.append(p)
                continue
            log("  ⚠ sin imagen IA; uso la miniatura de mapa")
            spec = dict(spec, **spec.get("fallback", {}))
        if spec.get("bg") == "map":
            ms = _find_scene(script, "map_route")
            md = dict(ms["data"])
            big = Image.new("RGB", (1920, 1080))
            S.draw_frame_base(big, 0, th, 0)
            bright = dict(th, land=S.mix(th["land"], (255, 255, 255), 0.18))
            S.s_map_route(big, 99, 100, md, bright)
            img = big.resize((W, H), Image.LANCZOS)
        else:
            img = Image.new("RGB", (W, H), th["bg"])
            glow = Image.new("RGB", (W, H), th["bg2"])
            mask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mask).ellipse([W * 0.35, -H * 0.3, W * 1.2, H * 1.2], fill=255)
            img.paste(glow, (0, 0), mask.filter(ImageFilter.GaussianBlur(120)))
        d = ImageDraw.Draw(img)
        # sombra a la izquierda para que el texto se lea
        shade = Image.new("L", (W, H), 0)
        sd = ImageDraw.Draw(shade)
        for x in range(W):
            sd.line([(x, 0), (x, H)], fill=int(170 * max(0.0, 1 - x / (W * 0.6))))
        img.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), shade)
        d = ImageDraw.Draw(img)
        target = None
        if spec.get("art") == "cross_section":
            cs = _find_scene(script, "cross_section")
            layers = cs["data"]["layers"]
            cx, cy, R = W * 0.74, H * 0.55, H * 0.40 * spec.get("art_scale", 1.0)
            halo = Image.new("L", (W, H), 0)
            ImageDraw.Draw(halo).ellipse([cx - R * 1.25, cy - R * 1.25, cx + R * 1.25, cy + R * 1.25], fill=150)
            img.paste(Image.new("RGB", (W, H), th["accent"]), (0, 0), halo.filter(ImageFilter.GaussianBlur(60)))
            d = ImageDraw.Draw(img)
            for L in reversed(layers):
                r = R * L["r"]
                col = th.get(L.get("color", ""), S.hexc(L["color"]) if str(L.get("color", "")).startswith("#") else th["panel"])
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col, outline=th["bg"], width=4)
            core = R * layers[0]["r"]
            for k in range(8):  # fibras
                a = k / 8 * 6.283
                fx, fy = cx + core * 0.55 * S.math.cos(a), cy + core * 0.55 * S.math.sin(a)
                d.ellipse([fx - 7, fy - 7, fx + 7, fy + 7], fill=(255, 255, 255))
            target = (cx, cy, core * 1.35)
        if spec.get("art") == "map":
            big = Image.new("RGB", (1920, 1080))
            md = dict(spec["map"])
            bright = dict(th, land=S.mix(th["land"], (255, 255, 255), 0.08))
            S.s_map_route(big, 99, 99.0001, md, bright)
            img = big.resize((W, H), Image.LANCZOS)
            shade2 = Image.new("L", (W, H), 0)
            s2 = ImageDraw.Draw(shade2)
            for x in range(W):
                s2.line([(x, 0), (x, H)], fill=int(140 * max(0.0, 1 - x / (W * 0.55))))
            img.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), shade2)
            d = ImageDraw.Draw(img)
            if spec.get("target"):
                P0 = S._proj(tuple(md["bbox"]), W, H)
                tx, ty = P0(*spec["target"])
                z = 1.06  # zoom final del mapa animado
                tx, ty = W / 2 + (tx - W / 2) * z, H / 2 + (ty - H / 2) * z
                target = (tx, ty, 95)
        if spec.get("art") == "plane":
            # cielo: degradado + nubes abajo + avión grande a la derecha
            sky = Image.new("RGB", (W, H))
            sd2 = ImageDraw.Draw(sky)
            for yy in range(H):
                k = yy / H
                sd2.line([(0, yy), (W, yy)], fill=S.mix((6, 14, 34), (40, 110, 190), k))
            img.paste(sky)
            cl = Image.new("L", (W, H), 0)
            cd = ImageDraw.Draw(cl)
            import random as _r
            rnd = _r.Random(3)
            for _ in range(40):
                cx_, cy_ = rnd.uniform(0, W), rnd.uniform(H * 0.78, H * 1.05)
                rr = rnd.uniform(60, 160)
                cd.ellipse([cx_ - rr * 1.6, cy_ - rr, cx_ + rr * 1.6, cy_ + rr], fill=235)
            img.paste(Image.new("RGB", (W, H), (235, 242, 250)), (0, 0), cl.filter(ImageFilter.GaussianBlur(18)))
            shade2 = Image.new("L", (W, H), 0)
            s2 = ImageDraw.Draw(shade2)
            for x in range(W):
                s2.line([(x, 0), (x, H)], fill=int(150 * max(0.0, 1 - x / (W * 0.6))))
            img.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), shade2)
            d = ImageDraw.Draw(img)
            pxc, pyc = W * 0.76, H * 0.40
            S.plane(d, pxc, pyc, W * 0.42, (245, 248, 255), angle=-0.08)
            d.line([(W * 0.55, H * 0.66), (W * 0.99, H * 0.66)], fill=th["accent2"], width=6)
            d.text((W * 0.97, H * 0.66 + 14), spec.get("art_label", ""), font=S.font("display", 64),
                   fill=th["accent2"], anchor="rt", stroke_width=5, stroke_fill=(0, 0, 0))
            target = (pxc + W * 0.02, pyc, W * 0.12)
        size = 160
        while True:
            f = S.font("display", size)
            lines = S.wrap(d, spec["text"].upper(), f, W * 0.54)
            asc, desc = f.getmetrics()
            if (len(lines) <= 2 or size <= 70) and len(lines) * (asc + desc + 18) <= H * 0.82:
                break
            size -= 6
        lh = asc + desc
        y = (H - len(lines) * (lh + 18)) / 2
        for line in lines:
            tw = d.textlength(line, font=f)
            d.rectangle([36, y - 4, 36 + tw + 44, y + lh + 4], fill=th["red"])
            d.text((58, y), line, font=f, fill=(255, 255, 255))
            y += lh + 18
        if target:
            tx, ty, tr = target
            d.ellipse([tx - tr, ty - tr, tx + tr, ty + tr], outline=th["red"], width=12)
            ax0, ay0, ax1, ay1 = tx - tr - 150, ty + tr + 60, tx - tr * 0.75, ty + tr * 0.55
            d.line([(ax0, ay0), (ax1, ay1)], fill=th["red"], width=16)
            d.polygon([(ax1 + 18, ay1 - 18), (ax1 - 38, ay1 - 6), (ax1 - 4, ay1 + 34)], fill=th["red"])
        p = out_dir / f"2 - MINIATURA {'ABC'[i]}.jpg"
        img.save(p, quality=93)
        paths.append(p)
    return paths


# ───────────────────────── orquestación ─────────────────────────

def build(script_path: Path, preview: int | None = None, make_short: bool = False) -> Path:
    t_start = time.time()
    script = json.loads(script_path.read_text("utf-8"))
    conf = yaml.safe_load((ROOT / "config/canales.yaml").read_text("utf-8"))
    cfg = conf["canales"][script["channel"]]
    th = S.theme_from(cfg.get("tema"))
    voice = Voice(cfg)
    _ensure_downloads()

    num = script["videoId"].split("-")[0]
    safe_title = re.sub(r'[\\/:*?"<>|]', "", script["title"]).strip()
    out_dir = ROOT / "salida" / cfg["nombre"] / f"{num} - {safe_title}"
    if out_dir.exists():
        for old in out_dir.iterdir():
            old.unlink()
    work = ROOT / "cache/anim" / script["videoId"]
    (work / "audio").mkdir(parents=True, exist_ok=True)
    (work / "clips").mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) aplanar escenas con su capítulo
    flat = []
    for ch in script["chapters"]:
        label = f"{ch['n']} · {ch['title']}" if ch["n"] else None
        if ch["n"] and ch.get("card", True):
            flat.append(({"type": "title_card", "data": {"n": ch["n"], "title": ch["title"]}, "minDuration": 2.6},
                         None, ch))
        for sc in ch["scenes"]:
            flat.append((sc, label, ch))
    if preview:
        flat = flat[:preview]

    # 2) voz por escena → duraciones
    log(f"Voz ({len(flat)} escenas)…")
    durs, wavs, timings, tts_chars = [], [], [], 0
    for i, (sc, _, _) in enumerate(flat):
        narr = sc.get("narration", "").strip()
        wav = work / "audio" / f"{i:03d}.wav"
        words = None
        if narr:
            speech, words = voice.say(narr, wav)
            d = speech + PAD
            tts_chars += len(narr)
        else:
            d = 0
            wav = None
        timings.append(words)
        durs.append(max(d, float(sc.get("minDuration", 0)), 1.0))
        wavs.append(wav)

    # 3) render en paralelo
    log("Render de escenas…")
    w, h = 1920, 1080
    jobs, t0 = [], 0.0
    burn = cfg.get("subtitulos_incrustados", True)
    for i, ((sc, chap, _), d, tm) in enumerate(zip(flat, durs, timings)):
        caps = scene_captions(sc["narration"], d - PAD, 7, tm) if burn and sc.get("narration") else []
        key = json.dumps([sc, d, chap, cfg.get("tema"), caps], sort_keys=True)
        clip = work / "clips" / f"{i:03d}_{hashlib.sha1(key.encode()).hexdigest()[:10]}.mp4"
        jobs.append((sc, d, th, t0, chap, clip, w, h, caps))
        t0 += d
    todo = [j for j in jobs if not j[5].exists()]  # re-render parcial: solo lo que cambió
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        for k, _ in enumerate(ex.map(_render_scene, todo), 1):
            if k % 10 == 0 or k == len(todo):
                log(f"  {k}/{len(todo)} escenas")

    # 4) audio completo (cada escena: su voz + silencio hasta su duración)
    log("Audio y montaje final…")
    parts = []
    for i, (wav, d) in enumerate(zip(wavs, durs)):
        seg = work / "audio" / f"seg_{i:03d}.wav"
        if wav:
            run_ffmpeg(["-i", str(wav), "-af", f"apad,atrim=0:{d:.3f}", "-ar", "24000", "-ac", "1", str(seg)])
        else:
            run_ffmpeg(["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{d:.3f}", str(seg)])
        parts.append(seg)
    (work / "audio.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    voice_wav = work / "voz.wav"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(work / "audio.txt"), "-c", "copy", str(voice_wav)])
    (work / "clips.txt").write_text("".join(f"file '{j[5].resolve()}'\n" for j in jobs))
    silent = work / "video_mudo.mp4"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(work / "clips.txt"), "-c", "copy", str(silent)])

    music = sorted((ROOT / "assets/musica").glob("*.mp3"))
    video = out_dir / "1 - VIDEO.mp4"
    voice_chain = "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[v]"
    if music:
        run_ffmpeg(["-i", str(silent), "-i", str(voice_wav), "-stream_loop", "-1", "-i", str(music[0]),
                    "-filter_complex", f"{voice_chain};[2:a]volume=0.12,aresample=48000[m];"
                    "[v][m]amix=inputs=2:duration=first:normalize=0[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(video)])
    else:
        run_ffmpeg(["-i", str(silent), "-i", str(voice_wav), "-filter_complex", voice_chain.replace("[v]", "[a]"),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(video)])

    # 5) subtítulos y capítulos
    srt, chapters, t = [], [], 0.0
    seen = set()
    for (sc, _, ch), d in zip(flat, durs):
        if ch["n"] not in seen:
            seen.add(ch["n"])
            chapters.append((t, ch.get("title_youtube", ch["title"]) if ch["n"] else script.get("hook_chapter", "Intro")))
        if sc.get("narration"):
            srt += _caption_chunks(sc["narration"], t, d - PAD, 8)
        t += d
    (out_dir / "5 - SUBTITULOS.srt").write_text(
        "\n".join(f"{i}\n{_srt_time(a)} --> {_srt_time(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(srt, 1)), "utf-8")

    # 6) miniaturas (3 variantes para la prueba A/B de YouTube)
    thumbs = thumbnails(script, th, out_dir)

    # 7) Short vertical (opcional)
    shorts = script.get("shorts") or ([script["short"]] if script.get("short") else [])
    short_texts = []
    if make_short:
        for k, sh in enumerate(shorts, 1):
            build_short(sh, k, th, voice, work, out_dir)
            short_texts += [f"════════ SHORT {k} (3 - SHORT {k}.mp4) ════════", "TÍTULO:", sh["title"], "",
                            "DESCRIPCIÓN:", sh["description"], ""]

    # 8) ficha de subida
    md = script["metadata"]
    total = t
    desc = md["description"].strip() + "\n\n" + "\n".join(f"{_fmt_ts(a)} {b}" for a, b in chapters)
    if script.get("sources"):
        desc += "\n\nSources:\n" + "\n".join(f"- {s['note']}: {s['url']}" for s in script["sources"])
    desc += "\n\n" + " ".join(md.get("hashtags", []))
    metadata = {"title": script["title"], "alt_titles": md.get("alt_titles", []), "description": desc,
                "tags": md.get("tags", []), "language": cfg["idioma"], "category": "Science & Technology",
                "duration_sec": round(total, 1), "chapters": [[_fmt_ts(a), b] for a, b in chapters]}
    (work / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), "utf-8")
    lines = [
        f"CANAL: {cfg['nombre']}   ·   DURACIÓN: {_fmt_ts(total)}",
        f"⏰ PROGRAMAR PUBLICACIÓN: {cfg['publicar']['video']} (hora de España)", "",
        "════════ VÍDEO LARGO (1 - VIDEO.mp4) ════════", "TÍTULO:", script["title"], "",
        "TÍTULOS ALTERNATIVOS (Probar y comparar):", *[f"  - {x}" for x in md.get("alt_titles", [])], "",
        "MINIATURAS: sube las 3 (A, B, C) en 'Probar y comparar' para que YouTube elija la mejor.", "",
        "DESCRIPCIÓN (con capítulos):", desc, "",
        "ETIQUETAS:", ", ".join(md.get("tags", [])), "",
        "SUBTÍTULOS: '5 - SUBTITULOS.srt' (Subtítulos → Añadir → Subir archivo → Con tiempos)", "",
        "COMENTARIO PARA FIJAR:", md.get("pinned_comment", ""), "",
        "CHECKLIST ANTES DE PUBLICAR:",
        "  [ ] Público: 'No, no es contenido para niños'",
        "  [ ] Contenido alterado o sintético: SÍ (voz generada por IA)",
        "  [ ] Pantalla final (últimos 20 s): vídeo recomendado a la izquierda + botón de suscribirse a la derecha",
        "  [ ] Doblaje automático activado", "",
        *short_texts,
        "════════ GUION ════════",
        *[sc.get("narration", "") for sc, _, _ in flat if sc.get("narration")],
    ]
    (out_dir / "4 - TEXTOS PARA SUBIR.txt").write_text("\n".join(lines), "utf-8")
    (work / "cost.json").write_text(json.dumps({
        "tts_chars": tts_chars, "render_seconds": round(time.time() - t_start), "scenes": len(flat),
        "claude": "guion escrito en sesión de Claude Code (sin API)"}, indent=2), "utf-8")
    log(f"✔ {video} ({_fmt_ts(total)}) · miniaturas: {len(thumbs)}")
    return video


def build_short(sh, k, th, voice, work, out_dir):
    """Short vertical 1080x1920 con subtítulos grandes a partir de sus escenas."""
    w, h = 1080, 1920
    sdir = work / f"short{k}"
    sdir.mkdir(exist_ok=True)
    jobs, parts, t0 = [], [], 0.0
    for i, sc in enumerate(sh["scenes"]):
        wav = sdir / f"{i:02d}.wav"
        speech, words = voice.say(sc["narration"], wav)
        d = speech + 0.15
        seg = sdir / f"seg_{i:02d}.wav"
        run_ffmpeg(["-i", str(wav), "-af", f"apad,atrim=0:{d:.3f}", "-ar", "24000", "-ac", "1", str(seg)])
        parts.append(seg)
        caps = scene_captions(sc["narration"], speech, 3, words)
        key = hashlib.sha1(json.dumps([sc, d, caps], sort_keys=True).encode()).hexdigest()[:10]
        jobs.append((sc, d, th, t0, None, sdir / f"clip_{i:02d}_{key}.mp4", w, h, caps))
        t0 += d
    todo = [j for j in jobs if not j[5].exists()]
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        list(ex.map(_render_scene, todo))
    (sdir / "a.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    (sdir / "v.txt").write_text("".join(f"file '{j[5].resolve()}'\n" for j in jobs))
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(sdir / "a.txt"), "-c", "copy", str(sdir / "voz.wav")])
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(sdir / "v.txt"), "-c", "copy", str(sdir / "mudo.mp4")])
    run_ffmpeg(["-i", str(sdir / "mudo.mp4"), "-i", str(sdir / "voz.wav"),
                "-filter_complex", "[1:a]loudnorm=I=-14:TP=-1.5,aresample=48000[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", str(out_dir / f"3 - SHORT {k}.mp4")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--preview", type=int)
    ap.add_argument("--short", action="store_true")
    a = ap.parse_args()
    script = Path(a.script).resolve()
    os.chdir(ROOT)
    build(script, a.preview, a.short)


if __name__ == "__main__":
    sys.exit(main())

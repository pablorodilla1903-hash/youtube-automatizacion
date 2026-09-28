"""Montaje con ffmpeg: clips de archivo + locución + música + subtítulos."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .broll import BrollPicker
from .tts import Word
from .util import log, run_ffmpeg

FPS = 30


@dataclass
class Segment:
    text: str
    broll: list[str]
    wav: Path
    duration: float
    words: list[Word] = field(default_factory=list)


def _fallback_image(path: Path, w: int, h: int, seed: int) -> Path:
    """Fondo degradado oscuro (si no hay clip de archivo disponible)."""
    rnd = random.Random(seed)
    base = [rnd.randint(10, 60) for _ in range(3)]
    accent = [min(255, c + rnd.randint(60, 140)) for c in base]
    img = Image.new("RGB", (w // 4, h // 4))
    draw = ImageDraw.Draw(img)
    for y in range(img.height):
        t = y / img.height
        draw.line([(0, y), (img.width, y)], fill=tuple(int(a * (1 - t) + b * t) for a, b in zip(accent, base)))
    img = img.resize((w, h)).filter(ImageFilter.GaussianBlur(8))
    img.save(path)
    return path


def _render_clip(src: Path, out: Path, frames: int, w: int, h: int, is_image: bool) -> None:
    scale = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    if is_image:
        # Efecto Ken Burns (zoom lento)
        vf = f"scale={w * 2}:{h * 2},zoompan=z='min(zoom+0.0006,1.15)':d={frames}:s={w}x{h}:fps={FPS},format=yuv420p"
        inp = ["-loop", "1", "-i", str(src)]
    else:
        vf = f"{scale},fps={FPS},format=yuv420p"
        inp = ["-stream_loop", "-1", "-i", str(src)]
    run_ffmpeg([
        *inp, "-frames:v", str(frames), "-vf", vf, "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", str(FPS), str(out),
    ])


def _ass_time(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def caption_chunks(words: list[Word], max_words: int) -> list[Word]:
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w[2].rstrip()[-1:] in ".,!?;:":
            chunks.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur)))
            cur = []
    if cur:
        chunks.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur)))
    # Si la pausa hasta el siguiente es corta, se mantiene en pantalla hasta entonces (sin parpadeos).
    out = []
    for i, (s, e, t) in enumerate(chunks):
        nxt = chunks[i + 1][0] if i + 1 < len(chunks) else None
        out.append((s, nxt if nxt is not None and 0 <= nxt - e < 0.6 else e, t))
    return out


def write_srt(chunks: list[Word], path: Path) -> None:
    lines = [f"{i}\n{_srt_time(s)} --> {_srt_time(e)}\n{t}\n" for i, (s, e, t) in enumerate(chunks, 1)]
    path.write_text("\n".join(lines), "utf-8")


def write_ass(chunks: list[Word], path: Path, w: int, h: int, vertical: bool, font: str) -> None:
    size, margin, outline = (92, int(h * 0.30), 6) if vertical else (58, 60, 4)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline},2,2,80,80,{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for s, e, t in chunks:
        t = t.replace("{", "(").replace("}", ")").replace("\n", " ")
        if vertical:
            t = t.upper()
        events.append(f"Dialogue: 0,{_ass_time(s)},{_ass_time(e)},Default,,0,0,0,,{t}")
    path.write_text(header + "\n".join(events) + "\n", "utf-8")


def render(
    segments: list[Segment],
    workdir: Path,
    out: Path,
    *,
    vertical: bool,
    picker: BrollPicker,
    music: Path | None,
    music_volume: float,
    burn_subs: bool,
    srt_out: Path | None,
) -> float:
    w, h = (1080, 1920) if vertical else (1920, 1080)
    clip_len = 3.2 if vertical else 6.5
    workdir.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    all_words: list[Word] = []
    t0 = 0.0
    frame_cursor = 0

    for i, seg in enumerate(segments):
        all_words += [(s + t0, e + t0, txt) for s, e, txt in seg.words]
        seg_end_frame = round((t0 + seg.duration) * FPS)
        seg_frames = seg_end_frame - frame_cursor
        n = max(1, round(seg.duration / clip_len))
        sources = picker.pick(seg.broll, n)
        for j in range(n):
            frames = seg_frames // n + (1 if j < seg_frames % n else 0)
            if frames <= 0:
                continue
            clip_out = workdir / f"clip_{i:03d}_{j:02d}.mp4"
            if sources:
                _render_clip(sources[j % len(sources)], clip_out, frames, w, h, is_image=False)
            else:
                img = _fallback_image(workdir / f"bg_{i:03d}_{j:02d}.png", w, h, seed=i * 31 + j)
                _render_clip(img, clip_out, frames, w, h, is_image=True)
            clips.append(clip_out)
        frame_cursor = seg_end_frame
        t0 += seg.duration
        log(f"    segmento {i + 1}/{len(segments)} listo ({seg.duration:.1f}s, {len(sources)} clips)")

    # Vídeo sin audio
    concat_list = workdir / "clips.txt"
    concat_list.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), "utf-8")
    silent = workdir / "video_mudo.mp4"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(silent)])

    # Locución completa
    wav_list = workdir / "voz.txt"
    wav_list.write_text("".join(f"file '{s.wav.resolve()}'\n" for s in segments), "utf-8")
    narration = workdir / "voz.wav"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(wav_list), "-c", "copy", str(narration)])

    # Subtítulos
    chunks = caption_chunks(all_words, 3 if vertical else 7)
    if srt_out:
        write_srt(chunks, srt_out)
    font_dir = Path("fonts")
    font = "Anton" if (font_dir / "Anton-Regular.ttf").exists() else "DejaVu Sans"

    inputs = ["-i", str(silent), "-i", str(narration)]
    voice_chain = "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[voz]"
    if music and music_volume > 0:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        audio_filter = (
            f"{voice_chain};[2:a]volume={music_volume},aresample=44100[mus];"
            "[voz][mus]amix=inputs=2:duration=first:normalize=0,afade=t=out:st={fade}:d=2[a]"
        ).replace("{fade}", f"{max(t0 - 2, 0):.2f}")
    else:
        audio_filter = voice_chain.replace("[voz]", "[a]")

    if burn_subs:
        ass = workdir / "subs.ass"
        write_ass(chunks, ass, w, h, vertical, font)
        fonts_opt = f":fontsdir={font_dir}" if font_dir.exists() else ""
        video_args = ["-filter_complex", f"[0:v]ass={ass}{fonts_opt}[v];{audio_filter}", "-map", "[v]",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
    else:
        video_args = ["-filter_complex", audio_filter, "-map", "0:v", "-c:v", "copy"]

    run_ffmpeg([*inputs, *video_args, "-map", "[a]", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", str(out)])
    return t0

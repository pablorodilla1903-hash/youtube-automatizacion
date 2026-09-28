"""Miniatura 1280x720: fotograma del vídeo + texto grande con contorno."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .util import bold_font, run_ffmpeg

HIGHLIGHT = (255, 214, 0)


def _wrap(draw: ImageDraw.ImageDraw, words: list[str], font, max_w: int) -> list[list[str]]:
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if cur and draw.textlength(test, font=font) > max_w:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def make_thumbnail(video: Path, text: str, highlight: str, out: Path, at: float = 4.0) -> None:
    W, H = 1280, 720
    frame = out.with_suffix(".frame.png")
    run_ffmpeg(["-ss", f"{at}", "-i", str(video), "-frames:v", "1",
                "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", str(frame)])
    img = Image.open(frame).convert("RGB")
    img = ImageEnhance.Contrast(ImageEnhance.Color(img).enhance(1.35)).enhance(1.15)

    # Oscurecer la mitad izquierda para que el texto se lea en el móvil
    shade = Image.new("L", (W, H))
    sd = ImageDraw.Draw(shade)
    for x in range(W):
        sd.line([(x, 0), (x, H)], fill=int(200 * max(0.0, 1 - x / (W * 0.8))))
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, shade)

    draw = ImageDraw.Draw(img)
    words = text.upper().split()
    hl = {w.strip(".,!?¡¿").upper() for w in highlight.split()} if highlight else set()
    max_w = int(W * 0.62)
    size = 170
    while size > 60:
        font = ImageFont.truetype(bold_font(), size)
        lines = _wrap(draw, words, font, max_w)
        line_h = int(size * 1.08)
        if len(lines) * line_h <= H * 0.8 and all(draw.textlength(" ".join(l), font=font) <= max_w for l in lines):
            break
        size -= 8
    y = (H - len(lines) * line_h) // 2
    for line in lines:
        x = 60
        for word in line:
            color = HIGHLIGHT if word.strip(".,!?¡¿") in hl else (255, 255, 255)
            draw.text((x, y), word, font=font, fill=color, stroke_width=max(4, size // 18), stroke_fill=(0, 0, 0))
            x += int(draw.textlength(word + " ", font=font))
        y += line_h
    img.save(out, quality=92)
    frame.unlink(missing_ok=True)

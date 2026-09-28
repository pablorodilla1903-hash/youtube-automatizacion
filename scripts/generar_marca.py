"""Genera logo, banner y marca de agua de cada canal en marca/<canal>/, con la paleta de config/canales.yaml.

Uso: python scripts/generar_marca.py [canal]
"""
import math
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ANTON = str(ROOT / "fonts/Anton-Regular.ttf")


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(size):
    return ImageFont.truetype(ANTON, size)


def blueprint_bg(w, h, th, step):
    img = Image.new("RGB", (w, h), th["bg"])
    glow = Image.new("L", (w // 8, h // 8), 0)
    ImageDraw.Draw(glow).ellipse([w // 8 * .15, h // 8 * .05, w // 8 * .85, h // 8 * .95], fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(w // 8 // 5)).resize((w, h))
    img.paste(Image.new("RGB", (w, h), th["bg2"]), (0, 0), glow)
    d = ImageDraw.Draw(img)
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=th["grid"], width=2)
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=th["grid"], width=2)
    return img


def gear(size, th, text):
    """Engranaje con monograma: icono del canal de ingeniería."""
    S = size * 2  # supermuestreo para bordes suaves
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = S / 2
    r_out, r_in, teeth = S * .47, S * .39, 12
    pts = []
    for i in range(teeth * 4):
        a = i / (teeth * 4) * 2 * math.pi
        r = r_out if (i % 4) in (1, 2) else r_in
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=th["accent"])
    d.ellipse([cx - S * .32, cy - S * .32, cx + S * .32, cy + S * .32], fill=th["bg"])
    d.ellipse([cx - S * .32, cy - S * .32, cx + S * .32, cy + S * .32], outline=th["accent"], width=int(S * .012))
    f = font(int(S * .30))
    d.text((cx, cy + S * .01), text, font=f, fill=th["text"], anchor="mm")
    return img.resize((size, size), Image.LANCZOS)


def globe(size, th, text):
    """Globo con meridianos: icono del canal de geografía."""
    S = size * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, r, lw = S / 2, S * .44, int(S * .03)
    d.ellipse([c - r, c - r, c + r, c + r], fill=th["accent"])
    ri = r - lw * 1.5
    d.ellipse([c - ri, c - ri, c + ri, c + ri], fill=th["bg"])
    for k in (0.35, 0.7):
        d.ellipse([c - ri * k, c - ri, c + ri * k, c + ri], outline=th["land"], width=lw // 2)
    for y in (-0.5, 0, 0.5):
        half = ri * math.sqrt(1 - y * y)
        d.line([(c - half, c + ri * y), (c + half, c + ri * y)], fill=th["land"], width=lw // 2)
    d.text((c, c), text, font=font(int(S * .30)), fill=th["text"], anchor="mm")
    return img.resize((size, size), Image.LANCZOS)


def make(cid, cfg):
    th = {k: hexc(v) for k, v in cfg["tema"].items()}
    words = cfg["nombre"].upper().split()
    mono = "".join(w[0] for w in words[:2])
    emblem = gear if cid == "ingenieria" else globe
    out = ROOT / "marca" / cid
    out.mkdir(parents=True, exist_ok=True)

    # Logo 800x800 (YouTube lo recorta en círculo: todo lo importante centrado)
    logo = blueprint_bg(800, 800, th, 80)
    g = emblem(600, th, mono)
    logo.paste(g, (100, 100), g)
    logo.save(out / "logo_800x800.png")

    # Banner 2560x1440 con el contenido dentro de la zona segura 1546x423
    W, H = 2560, 1440
    ban = blueprint_bg(W, H, th, 80)
    d = ImageDraw.Draw(ban)
    # esquema técnico decorativo a los lados (fuera de la zona segura: solo se ve en TV/escritorio)
    for side in (380, W - 380):
        for r in (120, 180, 240):
            d.ellipse([side - r, H / 2 - r, side + r, H / 2 + r], outline=th["panel"], width=4)
        d.line([(side - 300, H / 2), (side + 300, H / 2)], fill=th["panel"], width=3)
        d.line([(side, H / 2 - 300), (side, H / 2 + 300)], fill=th["panel"], width=3)
    x0, y0 = (W - 1546) // 2, (H - 423) // 2
    g = emblem(320, th, mono)
    ban.paste(g, (x0, y0 + 50), g)
    f = font(150)
    tx, ty = x0 + 370, y0 + 55
    first, rest = words[0] + " ", " ".join(words[1:])
    d.text((tx, ty), first, font=f, fill=th["accent"])
    d.text((tx + d.textlength(first, font=f), ty), rest, font=f, fill=th["text"])
    d.text((tx + 4, ty + 210), cfg.get("lema", ""), font=font(56), fill=th["muted"])
    ban.save(out / "banner_2560x1440.png")

    # Marca de agua 150x150
    wm = emblem(150, th, mono)
    wm.save(out / "marca_de_agua_150x150.png")
    print("OK", out)


if __name__ == "__main__":
    conf = yaml.safe_load((ROOT / "config/canales.yaml").read_text("utf-8"))["canales"]
    for cid, cfg in conf.items():
        if len(sys.argv) < 2 or cid in sys.argv[1:]:
            make(cid, cfg)

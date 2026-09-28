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


def globe(size, th, text=None, lon0=18.0, lat0=22.0):
    """Globo terráqueo con los continentes reales (Natural Earth) en proyección ortográfica."""
    import json

    S = size * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, r, lw = S / 2, S * .44, int(S * .035)
    d.ellipse([c - r, c - r, c + r, c + r], fill=th["accent"])
    R = r - lw * 1.3
    d.ellipse([c - R, c - R, c + R, c + R], fill=th["ocean"])
    la0, lo0 = math.radians(lat0), math.radians(lon0)

    def proj(lon, lat):
        la, lo = math.radians(lat), math.radians(lon)
        cosc = math.sin(la0) * math.sin(la) + math.cos(la0) * math.cos(la) * math.cos(lo - lo0)
        x = math.cos(la) * math.sin(lo - lo0)
        y = math.cos(la0) * math.sin(la) - math.sin(la0) * math.cos(la) * math.cos(lo - lo0)
        return (c + R * x, c - R * y), cosc >= 0

    geo = ROOT / "cache/geo/ne_110m_land.geojson"
    data = json.loads(geo.read_text("utf-8"))
    for f in data["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            pts, vis = zip(*(proj(lon, lat) for lon, lat in poly[0]))
            if sum(vis) > len(vis) * 0.5:
                d.polygon([p for p, v in zip(pts, vis) if v], fill=th["accent2"])
    # meridianos y paralelos finos
    for k in range(-60, 61, 30):
        line = [proj(lon, k) for lon in range(-180, 181, 3)]
        d.line([p for p, v in line if v], fill=th["bg2"], width=max(1, lw // 4))
    for m in range(-180, 180, 30):
        line = [proj(m, lat) for lat in range(-90, 91, 3)]
        d.line([p for p, v in line if v], fill=th["bg2"], width=max(1, lw // 4))
    return img.resize((size, size), Image.LANCZOS)


def compass_clock(size, th, text=None):
    """Brújula dentro de un reloj: geografía (rosa de los vientos) + historia (marcas del tiempo)."""
    S = size * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    gold, parch, dark = th["accent"], th["accent2"], th["bg"]
    R = S * .46
    d.ellipse([c - R, c - R, c + R, c + R], fill=gold)
    r2 = R * .9
    d.ellipse([c - r2, c - r2, c + r2, c + r2], fill=dark)
    # marcas del reloj (60 minutos, 12 horas más largas)
    for k in range(60):
        a = k / 60 * 2 * math.pi
        L = R * (.14 if k % 5 == 0 else .06)
        w_ = int(S * (.014 if k % 5 == 0 else .006))
        x0, y0 = c + (r2 - S * .02) * math.sin(a), c - (r2 - S * .02) * math.cos(a)
        x1, y1 = c + (r2 - S * .02 - L) * math.sin(a), c - (r2 - S * .02 - L) * math.cos(a)
        d.line([(x0, y0), (x1, y1)], fill=parch, width=w_)
    # rosa de los vientos: 8 puntas (4 largas doradas, 4 cortas)
    def star(n_len, width, rot, col_a, col_b):
        a = rot
        tip = (c + n_len * math.sin(a), c - n_len * math.cos(a))
        l = (c + width * math.sin(a - math.pi / 2), c - width * math.cos(a - math.pi / 2))
        rr = (c + width * math.sin(a + math.pi / 2), c - width * math.cos(a + math.pi / 2))
        d.polygon([tip, l, (c, c)], fill=col_a)
        d.polygon([tip, rr, (c, c)], fill=col_b)
    for k in range(4):
        star(R * .5, R * .1, math.pi / 4 + k * math.pi / 2, th["muted"], th["panel"])
    for k in range(4):
        star(R * .7, R * .13, k * math.pi / 2, gold, parch)
    d.ellipse([c - R * .07, c - R * .07, c + R * .07, c + R * .07], fill=dark, outline=gold, width=int(S * .01))
    return img.resize((size, size), Image.LANCZOS)


def world_backdrop(w, h, th):
    """Mapamundi antiguo muy tenue para el fondo del banner, con meridianos y paralelos."""
    import json
    img = Image.new("RGB", (w, h), th["bg"])
    d = ImageDraw.Draw(img)
    data = json.loads((ROOT / "cache/geo/ne_110m_land.geojson").read_text("utf-8"))
    def P(lon, lat):
        return ((lon + 180) / 360 * w, (84 - lat) / (84 + 58) * h)
    for lon in range(-180, 181, 15):
        d.line([P(lon, 84), P(lon, -58)], fill=th["grid"], width=2)
    for lat in range(-45, 84, 15):
        d.line([P(-180, lat), P(180, lat)], fill=th["grid"], width=2)
    for f_ in data["features"]:
        g = f_["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            d.polygon([P(lon, lat) for lon, lat in poly[0]], fill=th["land"])
    # viñeta para centrar la mirada
    vig = Image.new("L", (w // 8, h // 8), 0)
    ImageDraw.Draw(vig).ellipse([w // 8 * .12, h // 8 * .12, w // 8 * .88, h // 8 * .88], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(w // 8 // 10)).resize((w, h))
    dark = Image.new("RGB", (w, h), th["bg"])
    return Image.composite(img, dark, vig)


def make(cid, cfg):
    th = {k: hexc(v) for k, v in cfg.get("marca_tema", cfg["tema"]).items()}
    words = cfg["nombre"].upper().split()
    mono = "".join(w[0] for w in words[:2])
    emblem = {"ingenieria": gear, "atlas": compass_clock}.get(cid, globe)
    out = ROOT / "marca" / cid
    out.mkdir(parents=True, exist_ok=True)

    # Foto de perfil 800x800 (YouTube la recorta en círculo)
    logo = Image.new("RGB", (800, 800), th["bg"])
    glow = Image.new("L", (800, 800), 0)
    ImageDraw.Draw(glow).ellipse([60, 60, 740, 740], fill=120)
    logo.paste(Image.new("RGB", (800, 800), th["bg2"]), (0, 0), glow.filter(ImageFilter.GaussianBlur(90)))
    g = emblem(660, th, mono)
    logo.paste(g, (70, 70), g)
    logo.save(out / "logo_800x800.png")

    # Banner 2560x1440; el texto va dentro de la zona segura central (1546x423)
    W, H = 2560, 1440
    ban = world_backdrop(W, H, th)
    d = ImageDraw.Draw(ban)
    x0, y0 = (W - 1546) // 2, (H - 423) // 2
    g = emblem(360, th, mono)
    ban.paste(g, (x0 + 10, y0 + 32), g)
    tx, ty = x0 + 420, y0 + 40
    size = 170
    while d.textlength(" ".join(words), font=font(size)) > 1546 - 440 and size > 90:
        size -= 6
    f = font(size)
    first = words[0] + " "
    rest = " ".join(words[1:])
    d.text((tx, ty), first, font=f, fill=th["accent"], stroke_width=6, stroke_fill=th["bg"])
    d.text((tx + d.textlength(first, font=f), ty), rest, font=f, fill=th["text"], stroke_width=6, stroke_fill=th["bg"])
    d.text((tx + 6, ty + int(size * 1.3)), cfg.get("lema", ""), font=font(58), fill=th["accent2"], stroke_width=4, stroke_fill=th["bg"])
    ban.save(out / "banner_2560x1440.png")

    # Marca de agua 150x150 (PNG con transparencia)
    emblem(150, th, mono).save(out / "marca_de_agua_150x150.png")
    print("OK", out)


if __name__ == "__main__":
    conf = yaml.safe_load((ROOT / "config/canales.yaml").read_text("utf-8"))["canales"]
    for cid, cfg in conf.items():
        if len(sys.argv) < 2 or cid in sys.argv[1:]:
            make(cid, cfg)

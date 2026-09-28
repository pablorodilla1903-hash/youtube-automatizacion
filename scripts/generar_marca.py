"""Genera logo, banner y marca de agua de cada canal en marca/<canal>/, con la paleta de config/canales.yaml.

Uso: python scripts/generar_marca.py [canal]
"""
import math
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

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


def earth(size, th, lon0=20.0, lat0=18.0):
    """La Tierra en proyección ortográfica con continentes reales, luz lateral y atmósfera."""
    import json

    S = size * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    c, R = S / 2, S * 0.5 - 2
    ocean = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    od = ImageDraw.Draw(ocean)
    od.ellipse([c - R, c - R, c + R, c + R], fill=th["ocean"] + (255,))
    la0, lo0 = math.radians(lat0), math.radians(lon0)

    def proj(lon, lat):
        la, lo = math.radians(lat), math.radians(lon)
        cosc = math.sin(la0) * math.sin(la) + math.cos(la0) * math.cos(la) * math.cos(lo - lo0)
        x = math.cos(la) * math.sin(lo - lo0)
        y = math.cos(la0) * math.sin(la) - math.sin(la0) * math.cos(la) * math.cos(lo - lo0)
        return (c + R * x, c - R * y), cosc >= 0

    data = json.loads((ROOT / "cache/geo/ne_110m_land.geojson").read_text("utf-8"))
    for f in data["features"]:
        g = f["geometry"]
        for poly in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
            pts, vis = zip(*(proj(lon, lat) for lon, lat in poly[0]))
            if sum(vis) > len(vis) * 0.5:
                od.polygon([p for p, v in zip(pts, vis) if v], fill=th["land"] + (255,))
    # sombreado: luz desde arriba a la izquierda
    shade = Image.new("L", (S, S), 0)
    ImageDraw.Draw(shade).ellipse([c - R * 0.55, c - R * 0.15, c + R * 1.9, c + R * 2.2], fill=150)
    shade = shade.filter(ImageFilter.GaussianBlur(S // 10))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([c - R, c - R, c + R, c + R], fill=255)
    dark = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    ocean = Image.composite(dark, ocean, ImageChops.multiply(shade, mask))
    ocean.putalpha(mask)
    img.alpha_composite(ocean)
    return img.resize((size, size), Image.LANCZOS)


def timeline_earth_logo(size, th, text=None):
    """Tierra rodeada por un anillo de línea del tiempo (marcas y puntos de fechas)."""
    S = size * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    R = S * 0.47
    # anillo del tiempo: arco casi completo con marcas
    w = int(S * 0.028)
    d.arc([c - R, c - R, c + R, c + R], start=-80, end=250, fill=th["accent"], width=w)
    for k in range(0, 331, 11):
        a = math.radians(-80 + k)
        big = k % 55 == 0
        r1, r2 = R - w * (2.6 if big else 1.8), R - w * 1.1
        d.line([(c + r1 * math.cos(a), c + r1 * math.sin(a)), (c + r2 * math.cos(a), c + r2 * math.sin(a))],
               fill=th["accent2"], width=int(S * (0.012 if big else 0.006)))
    for k in (0, 110, 220):  # "fechas" destacadas
        a = math.radians(-80 + k)
        x, y = c + R * math.cos(a), c + R * math.sin(a)
        rr = S * 0.035
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=th["bg"], outline=th["accent"], width=int(S * 0.012))
    # flecha al final del arco (el tiempo avanza)
    a = math.radians(250)
    x, y = c + R * math.cos(a), c + R * math.sin(a)
    tang = a + math.pi / 2
    tip = (x + S * 0.075 * math.cos(tang), y + S * 0.075 * math.sin(tang))
    b1 = (x + S * 0.05 * math.cos(a), y + S * 0.05 * math.sin(a))
    b2 = (x - S * 0.05 * math.cos(a), y - S * 0.05 * math.sin(a))
    d.polygon([tip, b1, b2], fill=th["accent"])
    g = earth(int(S * 0.72), th)
    img.alpha_composite(g, (int(c - g.width / 2), int(c - g.height / 2)))
    return img.resize((size, size), Image.LANCZOS)


def timeline_banner(W, H, th, cfg):
    img = Image.new("RGB", (W, H), th["bg"])
    glow = Image.new("L", (W // 8, H // 8), 0)
    ImageDraw.Draw(glow).ellipse([W // 8 * .05, H // 8 * .1, W // 8 * .95, H // 8 * .9], fill=255)
    img.paste(Image.new("RGB", (W, H), th["bg2"]), (0, 0), glow.filter(ImageFilter.GaussianBlur(W // 8 // 7)).resize((W, H)))
    d = ImageDraw.Draw(img)
    rnd = __import__("random").Random(5)
    for _ in range(260):  # estrellas tenues
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.choice([1, 1, 2])
        d.ellipse([x - r, y - r, x + r, y + r], fill=S_mix(th["bg"], th["text"], rnd.uniform(.15, .5)))
    x0, y0 = (W - 1546) // 2, (H - 423) // 2
    # línea del tiempo de lado a lado, a la altura del centro de la zona segura
    ly = y0 + 352
    d.line([(0, ly), (W, ly)], fill=th["accent"], width=6)
    years = ["3000 BC", "1000 BC", "0", "1000", "1500", "1900", "TODAY"]
    xs = [x0 + 430 + i * (1546 - 470) / (len(years) - 1) for i in range(len(years))]
    fy = font(36)
    for i, (x, yr) in enumerate(zip(xs, years)):
        r = 14 if i < len(years) - 1 else 20
        d.ellipse([x - r, ly - r, x + r, ly + r], fill=th["bg"], outline=th["accent"], width=6)
        d.text((x, ly + 24), yr, font=fy, fill=th["muted"], anchor="mt")
    for x in range(0, W, 40):  # marcas finas por toda la línea
        d.line([(x, ly - 8), (x, ly)], fill=S_mix(th["bg"], th["accent"], .6), width=2)
    g = timeline_earth_logo(320, th)
    img.paste(g, (x0 + 40, y0 + 8), g)
    words = cfg["nombre"].upper().split()
    size = 175
    while d.textlength(" ".join(words), font=font(size)) > 1546 - 450 and size > 90:
        size -= 5
    f = font(size)
    tx, ty = x0 + 430, y0 + 20
    first = words[0] + " "
    d.text((tx, ty), first, font=f, fill=th["text"])
    d.text((tx + d.textlength(first, font=f), ty), " ".join(words[1:]), font=f, fill=th["accent"])
    d.text((tx + 4, ty + int(size * 1.22)), cfg.get("lema", ""), font=font(50), fill=th["accent2"])
    return img


def S_mix(a, b, k):
    return tuple(int(x + (y - x) * k) for x, y in zip(a, b))


def make(cid, cfg):
    th = {k: hexc(v) for k, v in cfg.get("marca_tema", cfg["tema"]).items()}
    words = cfg["nombre"].upper().split()
    mono = "".join(w[0] for w in words[:2])
    emblem = {"ingenieria": gear, "atlas": timeline_earth_logo}.get(cid, globe)
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
    if cid == "atlas":
        timeline_banner(W, H, th, cfg).save(out / "banner_2560x1440.png")
        emblem(150, th, mono).save(out / "marca_de_agua_150x150.png")
        print("OK", out)
        return
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

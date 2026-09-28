"""Genera logo, banner y marca de agua de cada canal en marca/<canal>/.

Uso: python scripts/generar_marca.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "fonts/Anton-Regular.ttf")
BLACK, YELLOW, WHITE, GREY = (11, 11, 11), (255, 214, 0), (255, 255, 255), (170, 170, 170)

CANALES = {
    "en": {
        "nombre": ("FORTUNE ", "FILES"),
        "lema": "THE UNTOLD STORIES BEHIND THE MONEY",
        "extra": "NEW STORY EVERY DAY",
        "simbolo": "$",
    },
    "es": {
        "nombre": ("EXPEDIENTE ", "FORTUNA"),
        "lema": "LAS HISTORIAS OCULTAS DETRÁS DEL DINERO",
        "extra": "NUEVA HISTORIA CADA DÍA",
        "simbolo": "$",
    },
}


def font(size):
    return ImageFont.truetype(FONT, size)


def folder_icon(size: int, symbol: str) -> Image.Image:
    """Icono de carpeta/expediente amarilla con el símbolo del dinero."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    r = int(s * 0.06)
    # pestaña + cuerpo
    d.rounded_rectangle([s * 0.10, s * 0.20, s * 0.48, s * 0.36], r, fill=YELLOW)
    d.rounded_rectangle([s * 0.10, s * 0.28, s * 0.90, s * 0.82], r, fill=YELLOW)
    # franja de la carpeta
    d.rectangle([s * 0.10, s * 0.36, s * 0.90, s * 0.39], fill=(215, 175, 0))
    f = font(int(s * 0.46))
    box = d.textbbox((0, 0), symbol, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text((s * 0.5 - w / 2 - box[0], s * 0.60 - h / 2 - box[1]), symbol, font=f, fill=BLACK)
    return img


def logo(cfg, out: Path):
    s = 800
    img = Image.new("RGB", (s, s), BLACK)
    glow = Image.new("RGB", (s, s), BLACK)
    ImageDraw.Draw(glow).ellipse([120, 120, 680, 680], fill=(70, 55, 0))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(120)), 1.0)
    icon = folder_icon(560, cfg["simbolo"])
    img.paste(icon, (120, 110), icon)
    img.save(out / "logo_800x800.png")


def banner(cfg, out: Path):
    W, H = 2560, 1440
    img = Image.new("RGB", (W, H), BLACK)
    # degradado dorado muy suave en el centro
    glow = Image.new("RGB", (W, H), BLACK)
    ImageDraw.Draw(glow).ellipse([700, 450, 1860, 990], fill=(60, 48, 0))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(220)), 1.0)
    d = ImageDraw.Draw(img)
    # zona segura (visible en todos los dispositivos): 1546x423 centrada
    x0, y0 = (W - 1546) // 2, (H - 423) // 2
    icon = folder_icon(300, cfg["simbolo"])
    img.paste(icon, (x0 + 10, y0 + 50), icon)
    a, b = cfg["nombre"]
    f = font(150)
    tx, ty = x0 + 330, y0 + 60
    d.text((tx, ty), a, font=f, fill=WHITE)
    d.text((tx + d.textlength(a, font=f), ty), b, font=f, fill=YELLOW)
    d.text((tx + 4, ty + 205), cfg["lema"], font=font(52), fill=GREY)
    d.text((tx + 4, ty + 275), cfg["extra"], font=font(40), fill=YELLOW)
    img.save(out / "banner_2560x1440.png")


def watermark(cfg, out: Path):
    s = 150
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, s - 1, s - 1], fill=BLACK + (255,))
    d.ellipse([10, 10, s - 11, s - 11], outline=YELLOW, width=5)
    d.text((s / 2, s / 2), "SUBSCRIBE" if cfg is CANALES["en"] else "SUSCRÍBETE", font=font(24),
           fill=YELLOW, anchor="mm")
    img.save(out / "marca_de_agua_150x150.png")


if __name__ == "__main__":
    for cid, cfg in CANALES.items():
        out = ROOT / "marca" / cid
        out.mkdir(parents=True, exist_ok=True)
        logo(cfg, out)
        banner(cfg, out)
        watermark(cfg, out)
        print("OK", out)

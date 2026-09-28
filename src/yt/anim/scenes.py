"""Biblioteca de escenas 2D animadas (Pillow). Cada escena dibuja un fotograma dado t (segundos).

Todas las escenas reciben (canvas, t, dur, data, theme) y dibujan sobre `canvas` (RGB 1920x1080
o 1080x1920). Reglas: entradas suaves (easing), un elemento principal en movimiento cada vez.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
FONTS = ROOT / "fonts"


# ───────────────────────── utilidades ─────────────────────────

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):  # cubic out
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def prog(t, start, length):
    return ease((t - start) / length) if length > 0 else float(t >= start)


def mix(c1, c2, a):
    a = clamp(a)
    return tuple(int(x + (y - x) * a) for x, y in zip(c1, c2))


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@lru_cache(maxsize=256)
def font(kind: str, size: int):
    if kind == "display":
        p = FONTS / "Anton-Regular.ttf"
        if p.exists():
            return ImageFont.truetype(str(p), size)
    p = FONTS / "Montserrat.ttf"
    if p.exists():
        f = ImageFont.truetype(str(p), size)
        f.set_variation_by_name({"bold": "ExtraBold", "semi": "SemiBold", "body": "Medium"}.get(kind, "Bold"))
        return f
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)


def text_w(d, s, f):
    return d.textlength(s, font=f)


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        test = (cur + " " + w).strip()
        if cur and text_w(d, test, f) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def fit_font(d, text, kind, max_w, max_lines, start, minimum=30):
    size = start
    while size > minimum:
        f = font(kind, size)
        if len(wrap(d, text, f, max_w)) <= max_lines:
            return f
        size -= 4
    return font(kind, minimum)


def norm_words(s):
    return re.sub(r"[^\w$%€]+", "", s.lower())


def reveal_words(d, text, box_center, f, max_w, t, start, per_word, th, highlight=(), align="center",
                 line_gap=1.12, color=None):
    """Dibuja texto palabra a palabra con fundido; las palabras de `highlight` van en color de acento."""
    color = color or th["text"]
    hl = {norm_words(h) for h in highlight}
    lines = wrap(d, text, f, max_w)
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * line_gap)
    total_h = lh * len(lines)
    cx, cy = box_center
    y = cy - total_h / 2
    i = 0
    for line in lines:
        words = line.split()
        lw = text_w(d, line, f)
        x = cx - lw / 2 if align == "center" else cx
        for w in words:
            a = prog(t, start + i * per_word, 0.35)
            if a > 0:
                c = th["accent"] if norm_words(w) in hl else color
                d.text((x, y + (1 - a) * 18), w, font=f, fill=mix(th["bg"], c, a))
            x += text_w(d, w + " ", f)
            i += 1
        y += lh
    return total_h


def rrect(d, box, r, **kw):
    d.rounded_rectangle([int(v) for v in box], radius=int(r), **kw)


# ───────────────────────── fondo y marco ─────────────────────────

@lru_cache(maxsize=4)
def background(w, h, bg, bg2):
    img = Image.new("RGB", (w, h), bg)
    glow = Image.new("L", (w // 8, h // 8), 0)
    ImageDraw.Draw(glow).ellipse([w // 8 * 0.15, -h // 8 * 0.3, w // 8 * 0.85, h // 8 * 0.9], fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(w // 8 // 6)).resize((w, h), Image.BILINEAR)
    img.paste(Image.new("RGB", (w, h), bg2), (0, 0), glow)
    return img


def draw_frame_base(canvas, t, th, global_t):
    w, h = canvas.size
    canvas.paste(background(w, h, th["bg"], th["bg2"]))
    d = ImageDraw.Draw(canvas)
    # rejilla tenue que se desplaza despacio (sensación de movimiento continuo)
    step = 120
    off = (global_t * 6) % step
    gc = mix(th["bg"], th["grid"], 1)
    for x in range(-step, w + step, step):
        d.line([(x + off, 0), (x + off, h)], fill=gc, width=1)
    for y in range(-step, h + step, step):
        d.line([(0, y + off * 0.5), (w, y + off * 0.5)], fill=gc, width=1)
    return d


def chapter_bar(d, th, chapter, vertical=False):
    if not chapter:
        return
    f = font("semi", 30 if not vertical else 34)
    label = chapter.upper()
    x, y = (60, 50) if not vertical else (60, 140)
    tw = text_w(d, label, f)
    rrect(d, [x, y, x + tw + 64, y + 58], 12, fill=th["panel"])
    d.rectangle([x, y, x + 8, y + 58], fill=th["accent"])
    d.text((x + 36, y + 11), label, font=f, fill=th["text"])


# ───────────────────────── iconos vectoriales ─────────────────────────

def icon(d, kind, x, y, s, color, bg):
    """Dibuja un icono simple en el cuadrado (x, y, s)."""
    if kind == "store":
        rrect(d, [x + s * .1, y + s * .35, x + s * .9, y + s * .95], s * .06, fill=color)
        d.polygon([(x + s * .05, y + s * .38), (x + s * .5, y + s * .08), (x + s * .95, y + s * .38)], fill=color)
        d.rectangle([x + s * .4, y + s * .6, x + s * .6, y + s * .95], fill=bg)
    elif kind == "disc":
        d.ellipse([x + s * .08, y + s * .08, x + s * .92, y + s * .92], fill=color)
        d.ellipse([x + s * .4, y + s * .4, x + s * .6, y + s * .6], fill=bg)
    elif kind == "envelope":
        rrect(d, [x + s * .05, y + s * .22, x + s * .95, y + s * .78], s * .06, fill=color)
        d.line([(x + s * .08, y + s * .26), (x + s * .5, y + s * .55), (x + s * .92, y + s * .26)], fill=bg,
               width=max(2, int(s * .07)))
    elif kind == "person":
        d.ellipse([x + s * .32, y + s * .08, x + s * .68, y + s * .44], fill=color)
        rrect(d, [x + s * .18, y + s * .5, x + s * .82, y + s * .95], s * .2, fill=color)
    elif kind == "tv":
        rrect(d, [x + s * .05, y + s * .15, x + s * .95, y + s * .75], s * .08, fill=color)
        rrect(d, [x + s * .13, y + s * .23, x + s * .87, y + s * .67], s * .04, fill=bg)
        d.polygon([(x + s * .4, y + s * .35), (x + s * .4, y + s * .57), (x + s * .6, y + s * .46)], fill=color)
        d.rectangle([x + s * .3, y + s * .8, x + s * .7, y + s * .86], fill=color)
    elif kind == "dollar":
        d.ellipse([x + s * .05, y + s * .05, x + s * .95, y + s * .95], fill=color)
        f = font("bold", int(s * .6))
        d.text((x + s / 2, y + s / 2), "$", font=f, fill=bg, anchor="mm")
    else:  # círculo genérico
        d.ellipse([x + s * .1, y + s * .1, x + s * .9, y + s * .9], fill=color)


# ───────────────────────── tipos de escena ─────────────────────────

def s_title_card(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    n = str(data.get("n", "")).zfill(2)
    a = prog(t, 0, 0.6)
    f_num = font("display", int(h * 0.30))
    d.text((w / 2, h * 0.40 + (1 - a) * 60), n, font=f_num, fill=mix(th["bg"], th["accent"], a), anchor="mm")
    f_k = font("semi", int(h * 0.035))
    d.text((w / 2, h * 0.19), data.get("kicker", "CHAPTER").upper(), font=f_k,
           fill=mix(th["bg"], th["muted"], prog(t, 0.2, 0.5)), anchor="mm")
    f_t = fit_font(d, data["title"].upper(), "display", w * 0.8, 2, int(h * 0.09))
    reveal_words(d, data["title"].upper(), (w / 2, h * 0.68), f_t, w * 0.8, t, 0.45, 0.12, th)
    lw = w * 0.18 * prog(t, 0.3, 0.8)
    d.rectangle([w / 2 - lw, h * 0.58, w / 2 + lw, h * 0.58 + 6], fill=th["accent"])


def _split_number(v: str):
    m = re.match(r"^(.*?)(\d[\d,]*(?:\.\d+)?)(.*)$", v)
    if not m:
        return None
    pre, num, suf = m.groups()
    dec = len(num.split(".")[1]) if "." in num else 0
    return pre, float(num.replace(",", "")), suf, dec, "," in num


def s_big_number(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    color = th.get(data.get("color", "accent"), th["accent"])
    val = str(data["value"])
    parts = _split_number(val)
    a = prog(t, 0, 1.3)
    if parts:
        pre, num, suf, dec, commas = parts
        cur = num * a
        s = f"{cur:,.{dec}f}" if commas else f"{cur:.{dec}f}"
        shown = f"{pre}{s}{suf}"
    else:
        shown = val
    if data.get("kicker"):
        d.text((w / 2, h * 0.24), data["kicker"].upper(), font=font("semi", int(h * 0.04)),
               fill=mix(th["bg"], th["muted"], prog(t, 0, 0.5)), anchor="mm")
    f_big = fit_font(d, val, "display", w * 0.86, 1, int(h * 0.26))
    scale_in = 0.85 + 0.15 * ease(t / 0.5)
    f_use = font("display", max(20, int(f_big.size * scale_in)))
    d.text((w / 2, h * 0.47), shown, font=f_use, fill=mix(th["bg"], color, prog(t, 0, 0.3)), anchor="mm")
    if data.get("caption"):
        f_c = fit_font(d, data["caption"], "bold", w * 0.8, 2, int(h * 0.055))
        reveal_words(d, data["caption"], (w / 2, h * 0.72), f_c, w * 0.8, t, 0.9, 0.08, th,
                     highlight=data.get("highlight", ()))


def s_text(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    if data.get("kicker"):
        k = data["kicker"].upper()
        f_k = font("semi", int(h * 0.036))
        a = prog(t, 0, 0.4)
        tw = text_w(d, k, f_k)
        rrect(d, [w / 2 - tw / 2 - 24, h * 0.22 - 30, w / 2 + tw / 2 + 24, h * 0.22 + 30], 30,
              fill=mix(th["bg"], th["panel"], a))
        d.text((w / 2, h * 0.22), k, font=f_k, fill=mix(th["bg"], th["accent"], a), anchor="mm")
    f = fit_font(d, data["text"], "display", w * 0.82, 3 if w > h else 4, int(h * (0.105 if w > h else 0.07)))
    per = min(0.14, max(0.05, (dur * 0.45) / max(1, len(data["text"].split()))))
    reveal_words(d, data["text"].upper() if data.get("upper", True) else data["text"], (w / 2, h * (0.53 if w > h else 0.38)), f,
                 w * 0.82, t, 0.15, per, th, highlight=[x.upper() for x in data.get("highlight", [])] + list(data.get("highlight", [])))


def s_quote(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    a = prog(t, 0, 0.5)
    d.text((w * 0.12, h * 0.16), "“", font=font("display", int(h * 0.35)), fill=mix(th["bg"], th["accent"], a))
    f = fit_font(d, data["text"], "bold", w * 0.72, 4, int(h * 0.07))
    reveal_words(d, data["text"], (w / 2, h * 0.5), f, w * 0.72, t, 0.3, 0.09, th,
                 highlight=data.get("highlight", ()))
    if data.get("author"):
        d.text((w / 2, h * 0.8), "— " + data["author"], font=font("semi", int(h * 0.04)),
               fill=mix(th["bg"], th["muted"], prog(t, 1.2, 0.5)), anchor="mm")


def s_timeline(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    ev = data["events"]
    focus = data.get("focus", len(ev) - 1)
    x0, x1, y = w * 0.1, w * 0.9, h * 0.58
    lp = prog(t, 0, 0.9)
    d.line([(x0, y), (x0 + (x1 - x0) * lp, y)], fill=th["muted"], width=6)
    n = len(ev)
    for i, e in enumerate(ev):
        x = x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0.5)
        a = prog(t, 0.3 + i * 0.18, 0.4)
        if a <= 0:
            continue
        is_f = i == focus
        r = (22 if is_f else 12) * a
        col = th["accent"] if is_f else th["text"]
        if is_f:
            pulse = 1 + 0.15 * math.sin(t * 4)
            d.ellipse([x - r * 1.8 * pulse, y - r * 1.8 * pulse, x + r * 1.8 * pulse, y + r * 1.8 * pulse],
                      outline=mix(th["bg"], th["accent"], 0.5), width=3)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        fy = font("display", int(h * (0.07 if is_f else 0.045)))
        d.text((x, y + h * 0.09), str(e["year"]), font=fy, fill=mix(th["bg"], col, a), anchor="mm")
        if is_f and e.get("label"):
            fl = fit_font(d, e["label"], "bold", w * 0.5, 2, int(h * 0.05))
            la = prog(t, 0.3 + i * 0.18 + 0.3, 0.5)
            lines = wrap(d, e["label"], fl, w * 0.5)
            asc, desc = fl.getmetrics()
            bh = (asc + desc) * len(lines) + 50
            bw = max(text_w(d, l, fl) for l in lines) + 70
            bx = min(max(x - bw / 2, w * 0.04), w * 0.96 - bw)
            by = y - h * 0.08 - bh - (1 - la) * 30
            rrect(d, [bx, by, bx + bw, by + bh], 18, fill=mix(th["bg"], th["panel"], la))
            ty = by + 25
            for l in lines:
                d.text((bx + bw / 2, ty), l, font=fl, fill=mix(th["bg"], th["text"], la), anchor="mt")
                ty += asc + desc
    if data.get("title"):
        d.text((w / 2, h * 0.16), data["title"].upper(), font=font("semi", int(h * 0.04)),
               fill=mix(th["bg"], th["muted"], prog(t, 0, 0.4)), anchor="mm")


def s_bars(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    bars = data["bars"]
    vmax = max(b["value"] for b in bars) or 1
    title = data.get("title", "")
    if title:
        f_t = fit_font(d, title.upper(), "display", w * 0.8, 1, int(h * 0.07))
        d.text((w / 2, h * 0.17), title.upper(), font=f_t, fill=mix(th["bg"], th["text"], prog(t, 0, 0.4)),
               anchor="mm")
    top, bottom = h * 0.28, h * 0.78
    n = len(bars)
    bh = min(120, (bottom - top) / n * 0.62)
    gap = (bottom - top) / n
    f_l = font("bold", int(min(bh * 0.5, h * 0.045)))
    f_v = font("display", int(min(bh * 0.75, h * 0.07)))
    lab_w = max(text_w(d, b["label"], f_l) for b in bars) + 40
    x0 = w * 0.08 + lab_w
    x1 = w * 0.84
    for i, b in enumerate(bars):
        y = top + gap * i + (gap - bh) / 2
        a = prog(t, 0.2 + i * 0.35, 0.9)
        col = th.get(b.get("color", ""), th["accent"] if i == data.get("highlight", -1) else th["text"])
        d.text((x0 - 30, y + bh / 2), b["label"], font=f_l, fill=mix(th["bg"], th["text"], prog(t, i * 0.35, .4)),
               anchor="rm")
        bw = (x1 - x0) * (b["value"] / vmax) * a
        if bw > 2:
            rrect(d, [x0, y, x0 + bw, y + bh], min(14, bh / 2), fill=col)
        if a > 0.05:
            d.text((x0 + bw + 20, y + bh / 2), b.get("display", str(b["value"])), font=f_v,
                   fill=mix(th["bg"], th["text"], a), anchor="lm")


def s_versus(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    L, R = data["left"], data["right"]
    for side, info, cx, delay in (("l", L, w * 0.27, 0), ("r", R, w * 0.73, 0.35)):
        a = prog(t, delay, 0.6)
        pw, ph = w * 0.38, h * 0.62
        off = (1 - a) * (-80 if side == "l" else 80)
        x0, y0 = cx - pw / 2 + off, h * 0.22
        col = th.get(info.get("color", "panel"), th["panel"])
        rrect(d, [x0, y0, x0 + pw, y0 + ph], 28, fill=mix(th["bg"], col, a))
        f_n = fit_font(d, info["name"].upper(), "display", pw * 0.85, 1, int(h * 0.09))
        d.text((x0 + pw / 2, y0 + ph * 0.16), info["name"].upper(), font=f_n,
               fill=mix(th["bg"], th.get(info.get("title_color", "text"), th["text"]), a), anchor="mm")
        f_l = fit_font(d, max(info.get("lines", [""]), key=len), "bold", pw * 0.85, 1, int(h * 0.05))
        for j, line in enumerate(info.get("lines", [])):
            la = prog(t, delay + 0.6 + j * 0.35, 0.4)
            d.text((x0 + pw / 2, y0 + ph * (0.38 + j * 0.16)), line, font=f_l,
                   fill=mix(th["bg"], th["text"], la), anchor="mm")
    va = prog(t, 0.5, 0.4)
    r = 70 * va
    if r > 1:
        d.ellipse([w / 2 - r, h * 0.53 - r, w / 2 + r, h * 0.53 + r], fill=th["accent"])
        d.text((w / 2, h * 0.53), "VS", font=font("display", int(60 * va) + 1), fill=th["bg"], anchor="mm")


def s_icon_grid(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    total = int(data.get("icons", 120))
    cols = int(data.get("cols", 20 if w > h else 10))
    rows = math.ceil(total / cols)
    area_w, area_h = w * 0.84, h * 0.44
    s = min(area_w / cols, area_h / rows)
    gx = (w - s * cols) / 2
    gy = h * 0.36
    mode = data.get("mode", "fill")
    keep = int(data.get("keep", 1))
    kind = data.get("icon", "store")
    fill_t = max(1.0, min(2.5, dur * 0.5))
    for i in range(total):
        r_, c_ = divmod(i, cols)
        x, y = gx + c_ * s, gy + r_ * s
        if mode == "fill":
            a = prog(t, (i / total) * fill_t, 0.25)
            hn = data.get("highlight")
            base_col = th["accent"] if hn is None or i < hn else th["muted"]
            if hn is not None and i >= hn:
                base_col = th.get(data.get("other_color", "muted"), th["muted"])
            col = mix(th["bg"], base_col, a)
            if a > 0:
                icon(d, kind, x + s * .1, y + s * .1, s * .8, col, th["bg"])
        else:  # drain: todos aparecen y se van apagando hasta dejar `keep`
            order = (i * 7919) % total  # orden pseudoaleatorio estable
            gone = order >= keep and t > 0.8 + (order / total) * fill_t
            col = th["accent"] if not gone else mix(th["bg"], th["grid"], 1)
            if i < keep and t > 0.8 + fill_t:
                col = mix(th["accent"], th["red"], 0.5 + 0.5 * math.sin(t * 5))
            icon(d, kind, x + s * .1, y + s * .1, s * .8, col, th["bg"])
    if data.get("label"):
        f = fit_font(d, data["label"].upper(), "display", w * 0.85, 1, int(h * 0.11))
        d.text((w / 2, h * 0.2), data["label"].upper(), font=f, fill=mix(th["bg"], th["text"], prog(t, 0, 0.5)),
               anchor="mm")
    if data.get("caption"):
        d.text((w / 2, h * 0.3), data["caption"], font=font("semi", int(h * 0.035)),
               fill=mix(th["bg"], th["muted"], prog(t, 0.3, 0.5)), anchor="mm")


def s_line_chart(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    pts = data["points"]
    col = th.get(data.get("color", "accent"), th["accent"])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = w * 0.1, w * 0.9, h * 0.72, h * 0.28
    ymax = data.get("ymax", max(ys) * 1.1 or 1)

    def P(p):
        return (x0 + (p[0] - xs[0]) / ((xs[-1] - xs[0]) or 1) * (x1 - x0), y0 - p[1] / ymax * (y0 - y1))

    d.line([(x0, y0), (x1, y0)], fill=th["muted"], width=3)
    a = prog(t, 0.2, max(1.5, dur * 0.55))
    n = len(pts)
    upto = a * (n - 1)
    k = int(upto)
    path = [P(p) for p in pts[:k + 1]]
    if k < n - 1:
        fa = upto - k
        pa, pb = P(pts[k]), P(pts[k + 1])
        path.append((pa[0] + (pb[0] - pa[0]) * fa, pa[1] + (pb[1] - pa[1]) * fa))
    if len(path) > 1:
        d.polygon(path + [(path[-1][0], y0), (path[0][0], y0)], fill=mix(th["bg"], col, 0.18))
        d.line(path, fill=col, width=8, joint="curve")
        ex, ey = path[-1]
        d.ellipse([ex - 14, ey - 14, ex + 14, ey + 14], fill=col)
    f_x = font("semi", int(h * 0.035))
    for lab in data.get("xlabels", []):
        px, _ = P((lab[0], 0))
        d.text((px, y0 + 40), str(lab[1]), font=f_x, fill=th["muted"], anchor="mm")
    if data.get("title"):
        f_t = fit_font(d, data["title"].upper(), "display", w * 0.8, 1, int(h * 0.07))
        d.text((w / 2, h * 0.16), data["title"].upper(), font=f_t,
               fill=mix(th["bg"], th["text"], prog(t, 0, 0.4)), anchor="mm")
    if data.get("end_label") and a > 0.95:
        ex, ey = path[-1]
        d.text((ex - 20, ey - 40), data["end_label"], font=font("display", int(h * 0.06)), fill=col, anchor="rb")


def s_stamp(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    pw, ph = w * 0.42, h * 0.72
    px, py = (w - pw) / 2, h * 0.16
    a = prog(t, 0, 0.5)
    rrect(d, [px, py + (1 - a) * 60, px + pw, py + ph + (1 - a) * 60], 16, fill=mix(th["bg"], (238, 234, 222), a))
    if data.get("doc_title"):
        d.text((w / 2, py + ph * 0.1), data["doc_title"].upper(), font=font("bold", int(h * 0.04)),
               fill=mix(th["bg"], (40, 40, 40), a), anchor="mm")
    for i in range(9):
        lw = pw * (0.75 if i % 3 else 0.55)
        yy = py + ph * (0.22 + i * 0.075)
        d.rectangle([px + pw * 0.12, yy, px + pw * 0.12 + lw * prog(t, 0.2 + i * 0.05, .3), yy + 10],
                    fill=mix(th["bg"], (170, 170, 170), a))
    st = 0.9
    if t >= st:
        sa = prog(t, st, 0.25)
        scale = 1.6 - 0.6 * sa
        stamp = _stamp_img(data["text"].upper(), int(h * 0.12), th["red"])
        sw, sh = int(stamp.width * scale), int(stamp.height * scale)
        img = stamp.resize((sw, sh), Image.BILINEAR)
        if sa < 1:
            alpha = img.getchannel("A").point(lambda v: int(v * sa))
            img.putalpha(alpha)
        c.paste(img, (int(w / 2 - sw / 2), int(h * 0.52 - sh / 2)), img)


@lru_cache(maxsize=8)
def _stamp_img(text, size, color):
    f = font("display", size)
    tmp = Image.new("RGBA", (10, 10))
    tw = int(ImageDraw.Draw(tmp).textlength(text, font=f))
    img = Image.new("RGBA", (tw + 80, int(size * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, img.width - 6, img.height - 6], 18, outline=color + (255,), width=10)
    d.text((img.width / 2, img.height / 2), text, font=f, fill=color + (255,), anchor="mm")
    return img.rotate(-12, expand=True, resample=Image.BICUBIC)


def s_list(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    if data.get("title"):
        f_t = fit_font(d, data["title"].upper(), "display", w * 0.8, 1, int(h * 0.08))
        d.text((w / 2, h * 0.18), data["title"].upper(), font=f_t,
               fill=mix(th["bg"], th["text"], prog(t, 0, .4)), anchor="mm")
    items = data["items"]
    step = min(dur * 0.7 / max(1, len(items)), 1.4)
    f = fit_font(d, max(items, key=len), "bold", w * 0.62, 1, int(h * 0.055))
    y0 = h * 0.34
    gap = min(h * 0.11, h * 0.46 / max(1, len(items)))
    for i, it in enumerate(items):
        a = prog(t, 0.3 + i * step, 0.45)
        if a <= 0:
            continue
        y = y0 + i * gap
        x = w * 0.2 + (1 - a) * -40
        mark = data.get("marks", ["check"] * len(items))[i]
        col = th["green"] if mark == "check" else th["red"]
        d.ellipse([x, y - 26, x + 52, y + 26], fill=mix(th["bg"], col, a))
        if mark == "check":
            d.line([(x + 14, y), (x + 23, y + 10), (x + 39, y - 11)], fill=th["bg"], width=7)
        else:
            d.line([(x + 16, y - 10), (x + 36, y + 10)], fill=th["bg"], width=7)
            d.line([(x + 36, y - 10), (x + 16, y + 10)], fill=th["bg"], width=7)
        d.text((x + 80, y), it, font=f, fill=mix(th["bg"], th["text"], a), anchor="lm")


def s_end_screen(c, t, dur, data, th):
    d = ImageDraw.Draw(c)
    w, h = c.size
    # huecos para los elementos de pantalla final de YouTube (vídeo a la izquierda, suscribirse a la derecha)
    a = prog(t, 0, 0.6)
    vx, vy, vw, vh = w * 0.08, h * 0.3, w * 0.46, w * 0.46 * 9 / 16
    rrect(d, [vx, vy, vx + vw, vy + vh], 20, outline=mix(th["bg"], th["accent"], a), width=6)
    d.text((vx + vw / 2, vy - 40), data.get("next_label", "WATCH NEXT").upper(), font=font("display", int(h * .05)),
           fill=mix(th["bg"], th["accent"], a), anchor="mm")
    if data.get("next_title"):
        f = fit_font(d, data["next_title"], "bold", vw * 0.85, 3, int(h * .05))
        reveal_words(d, data["next_title"], (vx + vw / 2, vy + vh / 2), f, vw * 0.85, t, 0.3, 0.05, th)
    cx, cy, r = w * 0.76, vy + vh / 2, h * 0.17
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=mix(th["bg"], th["text"], a), width=6)
    d.text((cx, cy + r + 50), data.get("sub_label", "SUBSCRIBE").upper(), font=font("display", int(h * .05)),
           fill=mix(th["bg"], th["text"], a), anchor="mm")
    if data.get("text"):
        f = fit_font(d, data["text"].upper(), "display", w * 0.8, 1, int(h * .08))
        d.text((w / 2, h * 0.15), data["text"].upper(), font=f, fill=mix(th["bg"], th["text"], a), anchor="mm")


SCENES = {
    "title_card": s_title_card,
    "big_number": s_big_number,
    "text": s_text,
    "quote": s_quote,
    "timeline": s_timeline,
    "bars": s_bars,
    "versus": s_versus,
    "icon_grid": s_icon_grid,
    "line_chart": s_line_chart,
    "stamp": s_stamp,
    "list": s_list,
    "end_screen": s_end_screen,
}


def theme_from(cfg: dict) -> dict:
    base = {
        "bg": "#0D1117", "bg2": "#1A2130", "grid": "#151B26", "panel": "#1F2937",
        "text": "#F5F5F5", "muted": "#8B95A7", "accent": "#FFD600", "red": "#FF3B3B", "green": "#22C55E",
        "blue": "#2F6BFF",
    }
    base.update(cfg or {})
    return {k: hexc(v) if isinstance(v, str) and v.startswith("#") else v for k, v in base.items()}


def draw_captions(canvas, th, captions, t):
    """captions: [(inicio, fin, [(palabra, t_inicio, t_fin), ...])] relativos a la escena."""
    for start, end, words in captions or []:
        if start <= t < end:
            break
    else:
        return
    d = ImageDraw.Draw(canvas)
    w, h = canvas.size
    vertical = w < h
    f = font("bold", int(h * (0.036 if vertical else 0.05)))
    text = " ".join(x[0] for x in words)
    lines = wrap(d, text, f, w * (0.86 if vertical else 0.8))
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * 1.08)
    box_h = lh * len(lines) + 34
    y_base = h * (0.80 if vertical else 0.935)
    y = y_base - box_h
    widest = max(text_w(d, l, f) for l in lines)
    rrect(d, [w / 2 - widest / 2 - 30, y, w / 2 + widest / 2 + 30, y + box_h], 16, fill=(8, 10, 14))
    y += 17
    i = 0
    for line in lines:
        x = w / 2 - text_w(d, line, f) / 2
        for word in line.split():
            _, ws, we = words[i]
            col = th["accent2"] if "accent2" in th and ws <= t < we + 0.05 else (255, 255, 255)
            d.text((x, y), word, font=f, fill=col)
            x += text_w(d, word + " ", f)
            i += 1
        y += lh


def render_frame(canvas, scene: dict, t: float, dur: float, th: dict, global_t: float, chapter: str | None,
                 captions=None):
    d = draw_frame_base(canvas, t, th, global_t)
    SCENES[scene["type"]](canvas, t, dur, scene.get("data", {}), th)
    if scene["type"] not in ("title_card", "end_screen"):
        chapter_bar(d, th, chapter, vertical=canvas.size[0] < canvas.size[1])
    draw_captions(canvas, th, captions, t)
    # fundido de salida corto para que el corte entre escenas sea suave
    fade = clamp((dur - t) / 0.18)
    if fade < 1:
        canvas.paste(Image.blend(Image.new("RGB", canvas.size, th["bg"]), canvas, fade))


# ───────────────────────── mapas, cortes y diagramas ─────────────────────────

import json as _json  # noqa: E402

GEO = ROOT / "cache/geo/ne_110m_land.geojson"


def _geo(name):
    return _json.loads((ROOT / "cache/geo" / f"{name}.geojson").read_text("utf-8"))


def _rings(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [p[0] for p in polys]


@lru_cache(maxsize=2)
def _land_polys(res="110m"):
    p = ROOT / "cache/geo" / f"ne_{res}_land.geojson"
    data = _json.loads((p if p.exists() else GEO).read_text("utf-8"))
    return [r for f in data["features"] for r in _rings(f["geometry"])]


@lru_cache(maxsize=1)
def _countries():
    try:
        data = _geo("ne_50m_admin_0_countries")
    except FileNotFoundError:
        return {}
    return {f["properties"]["NAME"]: _rings(f["geometry"]) for f in data["features"]}


@lru_cache(maxsize=1)
def _lakes():
    try:
        return [(f["properties"].get("name"), r) for f in _geo("ne_50m_lakes")["features"] for r in _rings(f["geometry"])]
    except FileNotFoundError:
        return []


@lru_cache(maxsize=1)
def _rivers():
    try:
        data = _geo("ne_50m_rivers_lake_centerlines")
    except FileNotFoundError:
        return {}
    out = {}
    for f in data["features"]:
        g = f["geometry"]
        lines = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        for key in {f["properties"].get("name"), f["properties"].get("name_en")}:
            if key:
                out.setdefault(key, []).extend(lines)
    return out


def _proj(bbox, w, h):
    lon0, lat0, lon1, lat1 = bbox
    # equirectangular con corrección de latitud media (evita mapas "aplastados")
    k = math.cos(math.radians((lat0 + lat1) / 2))
    sx = w / ((lon1 - lon0) * k)
    sy = h / (lat1 - lat0)
    s = min(sx, sy)
    ox = (w - (lon1 - lon0) * k * s) / 2
    oy = (h - (lat1 - lat0) * s) / 2

    def P(lon, lat):
        return (ox + (lon - lon0) * k * s, oy + (lat1 - lat) * s)

    return P


@lru_cache(maxsize=16)
def _map_image(bbox, w, h, land, ocean, border, extras="{}"):
    """Mapa base estático (se cachea por escena): tierra, lagos, fronteras y países resaltados."""
    ex = _json.loads(extras)
    S2 = 2
    img = Image.new("RGB", (w * S2, h * S2), ocean)
    d = ImageDraw.Draw(img)
    P = _proj(bbox, w * S2, h * S2)
    res = "50m" if (bbox[2] - bbox[0]) < 100 else "110m"

    def visible(pts):
        return not (max(p[0] for p in pts) < 0 or min(p[0] for p in pts) > w * S2
                    or max(p[1] for p in pts) < 0 or min(p[1] for p in pts) > h * S2)

    for shift in (-360, 0, 360):
        for ring in _land_polys(res):
            pts = [P(lon + shift, lat) for lon, lat in ring]
            if visible(pts):
                d.polygon(pts, fill=land)
    for hc in ex.get("highlight", []):
        for ring in _countries().get(hc["name"], []):
            d.polygon([P(lon, lat) for lon, lat in ring], fill=tuple(hc["color"]))
    if ex.get("borders", True) and res == "50m":
        for rings in _countries().values():
            for ring in rings:
                pts = [P(lon, lat) for lon, lat in ring]
                if visible(pts):
                    d.line(pts + [pts[0]], fill=border, width=3)
    if res == "50m":
        for _, ring in _lakes():
            pts = [P(lon, lat) for lon, lat in ring]
            if visible(pts):
                d.polygon(pts, fill=ocean)
    return img.resize((w, h), Image.LANCZOS)


def _route_pts(route, P):
    pts = []
    prev = None
    for lon, lat in route:
        if prev is not None and abs(lon - prev) > 180:  # cruza el antimeridiano
            lon += 360 if lon < prev else -360
        pts.append(P(lon, lat))
        prev = lon
    return pts


def _partial(pts, a):
    if a <= 0 or len(pts) < 2:
        return pts[:1]
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg) * a
    out = [pts[0]]
    for i, L in enumerate(seg):
        if total >= L:
            out.append(pts[i + 1])
            total -= L
        else:
            f = total / L if L else 0
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f))
            break
    return out


def s_map_route(c, t, dur, data, th):
    """Mapa del mundo (Natural Earth) con rutas animadas, puntos y etiquetas.

    data: bbox [lon0, lat0, lon1, lat1], routes [{points:[[lon,lat]...], color, label}],
          points [{lon, lat, label, anchor}], title, zoom (1→1.08 lento)
    """
    w, h = c.size
    bbox = tuple(data.get("bbox", [-180, -60, 180, 80]))
    extras = {"borders": data.get("borders", True),
              "highlight": [{"name": hc["name"], "color": list(mix(th.get("land", th["panel"]),
                             th.get(hc.get("color", "accent"), th["accent"]), hc.get("strength", 0.35)))}
                            for hc in data.get("highlight_countries", [])]}
    base = _map_image(bbox, w, h, th.get("land", th["panel"]), th.get("ocean", th["bg"]),
                      mix(th.get("land", th["panel"]), th["text"], 0.18), _json.dumps(extras, sort_keys=True))
    z = 1 + 0.06 * ease_io(t / max(dur, 0.1))  # zoom lento continuo
    if z > 1.001:
        cw, ch = int(w / z), int(h / z)
        base = base.crop(((w - cw) // 2, (h - ch) // 2, (w + cw) // 2, (h + ch) // 2)).resize((w, h), Image.BILINEAR)
    c.paste(base)
    d = ImageDraw.Draw(c)
    P0 = _proj(bbox, w, h)

    def P(lon, lat):
        x, y = P0(lon, lat)
        return (w / 2 + (x - w / 2) * z, h / 2 + (y - h / 2) * z)

    for poly in data.get("polygons", []):  # zonas (p. ej. el delta), aparecen con fundido
        a = prog(t, poly.get("start", 0.4), 0.6)
        if a > 0:
            col = th.get(poly.get("color", "green"), th["green"])
            d.polygon([P(lon, lat) for lon, lat in poly["points"]], fill=mix(th.get("land", th["panel"]), col, 0.75 * a))
    for rv in data.get("rivers", []):  # ríos por nombre; `band` = franja habitada a su alrededor
        a = prog(t, rv.get("start", 0.2), rv.get("grow", 1.2))
        col = th.get(rv.get("color", "blue"), th.get("blue", th["accent"]))
        for name in rv["names"]:
            for line in _rivers().get(name, []):
                pts = [P(lon, lat) for lon, lat in line]
                if rv.get("band"):
                    bw = int(rv["band"] * (0.3 + 0.7 * a))
                    d.line(pts, fill=mix(th.get("land", th["panel"]), th.get(rv.get("band_color", "green"), th["green"]), 0.8 * a),
                           width=max(1, bw), joint="curve")
        for name in rv["names"]:
            for line in _rivers().get(name, []):
                pts = [P(lon, lat) for lon, lat in line]
                d.line(pts, fill=mix(th.get("land", th["panel"]), col, a), width=rv.get("width", 6), joint="curve")
    for lb in data.get("labels", []):  # etiquetas de texto libres sobre el mapa
        a = prog(t, lb.get("start", 0.5), 0.5)
        if a > 0:
            x, y = P(lb["lon"], lb["lat"])
            d.text((x, y), lb["text"], font=font(lb.get("font", "bold"), int(h * lb.get("size", 0.04))),
                   fill=mix(th["bg"], th.get(lb.get("color", "text"), th["text"]), a), anchor="mm",
                   stroke_width=4, stroke_fill=th["bg"])
    routes = data.get("routes", [])
    rt = max(1.2, min(3.0, dur * 0.5))
    for i, r in enumerate(routes):
        start = 0.3 + (i * rt * 0.6 if len(routes) <= 3 else i * 0.12)
        a = prog(t, start, rt if len(routes) <= 3 else 1.0)
        pts = _partial(_route_pts(r["points"], P), a)
        col = th.get(r.get("color", "accent"), th["accent"])
        if len(pts) > 1:
            d.line(pts, fill=mix(th["bg"], col, 0.35), width=14, joint="curve")
            d.line(pts, fill=col, width=6, joint="curve")
            hx, hy = pts[-1]
            if a < 1:
                d.ellipse([hx - 11, hy - 11, hx + 11, hy + 11], fill=th["text"])
        if r.get("label") and a >= 1:
            mid = _route_pts(r["points"], P)[len(r["points"]) // 2]
            la = prog(t, start + rt, 0.4)
            f = font("bold", int(h * 0.038))
            tw = text_w(d, r["label"], f)
            rrect(d, [mid[0] - tw / 2 - 22, mid[1] - 80, mid[0] + tw / 2 + 22, mid[1] - 22], 12,
                  fill=mix(th["bg"], th["panel"], la))
            d.text((mid[0], mid[1] - 51), r["label"], font=f, fill=mix(th["bg"], th["text"], la), anchor="mm")
    for j, p in enumerate(data.get("points", [])):
        a = prog(t, 0.1 + j * 0.25, 0.4)
        if a <= 0:
            continue
        x, y = P(p["lon"], p["lat"])
        col = th.get(p.get("color", "accent2"), th.get("accent2", th["accent"]))
        pr = 12 + 6 * math.sin(t * 4 + j)
        d.ellipse([x - pr * 1.8, y - pr * 1.8, x + pr * 1.8, y + pr * 1.8], outline=mix(th["bg"], col, a * .6), width=3)
        d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=mix(th["bg"], col, a))
        if p.get("label"):
            f = font("bold", int(h * 0.036))
            anchor = p.get("anchor", "lm")
            dx = {"lm": 30, "rm": -30, "mb": 0, "mt": 0}.get(anchor, 30)
            dy = {"mb": -30, "mt": 30}.get(anchor, 0)
            d.text((x + dx, y + dy), p["label"], font=f, fill=mix(th["bg"], th["text"], a), anchor=anchor,
                   stroke_width=4, stroke_fill=th["bg"])
    if data.get("title"):
        f = fit_font(d, data["title"].upper(), "display", w * 0.8, 1, int(h * 0.075))
        tw = text_w(d, data["title"].upper(), f)
        a = prog(t, 0, 0.4)
        ty = h * 0.12
        rrect(d, [w / 2 - tw / 2 - 40, ty - 55, w / 2 + tw / 2 + 40, ty + 55], 16, fill=mix(th["bg"], th["panel"], a))
        d.text((w / 2, ty), data["title"].upper(), font=f, fill=mix(th["bg"], th["text"], a), anchor="mm")


def s_cross_section(c, t, dur, data, th):
    """Corte transversal con capas concéntricas que aparecen de dentro hacia fuera, con etiquetas."""
    d = ImageDraw.Draw(c)
    w, h = c.size
    layers = data["layers"]  # de dentro a fuera: {label, color, r (0-1)}
    cx, cy = (w * 0.33, h * 0.54) if w > h else (w * 0.5, h * 0.4)
    R = min(w, h) * 0.34
    step = max(0.35, min(0.8, dur * 0.6 / len(layers)))
    hl = data.get("highlight")
    for i in range(len(layers) - 1, -1, -1):
        L = layers[i]
        a = prog(t, 0.2 + i * step, 0.5)
        if a <= 0:
            continue
        r = R * L["r"] * (0.85 + 0.15 * a)
        col = th.get(L.get("color", ""), hexc(L["color"]) if str(L.get("color", "")).startswith("#") else th["panel"])
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=mix(th["bg"], col, a), outline=th["bg"], width=3)
    f = fit_font(d, max((L["label"] for L in layers), key=len), "bold", w * 0.34, 1, int(h * 0.042))
    for i, L in enumerate(layers):
        a = prog(t, 0.35 + i * step, 0.4)
        if a <= 0:
            continue
        ang = math.radians(-55 + i * (110 / max(1, len(layers) - 1)))
        r = R * L["r"] * 0.92 if i else 0
        px, py = cx + r * math.cos(ang), cy + r * math.sin(ang)
        lx = cx + R * 1.25 if w > h else w * 0.1
        ly = h * 0.22 + i * (h * 0.64 / max(1, len(layers) - 1)) if w > h else h * 0.72 + i * 60
        col = th["accent"] if hl == i else th["text"]
        d.line([(px, py), (lx - 20, ly)], fill=mix(th["bg"], th["muted"], a), width=3)
        d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=mix(th["bg"], th["text"], a))
        d.text((lx, ly), L["label"], font=f, fill=mix(th["bg"], col, a), anchor="lm")
    if data.get("title"):
        d.text((w / 2, h * 0.1), data["title"].upper(), font=font("display", int(h * 0.06)),
               fill=mix(th["bg"], th["text"], prog(t, 0, 0.4)), anchor="mm")


def s_diagram(c, t, dur, data, th):
    """Bloques y flechas que aparecen por pasos; opcionalmente un pulso de luz recorre las conexiones."""
    d = ImageDraw.Draw(c)
    w, h = c.size
    nodes = data["nodes"]  # {id, label, x, y (0-1), color?, icon?}
    edges = data.get("edges", [])  # [from, to, label?]
    step = max(0.3, min(0.7, dur * 0.5 / max(1, len(nodes))))
    pos = {n["id"]: (n["x"] * w, n["y"] * h) for n in nodes}
    order = {n["id"]: i for i, n in enumerate(nodes)}
    for e in edges:
        a_, b_ = e[0], e[1]
        start = 0.2 + max(order[a_], order[b_]) * step
        a = prog(t, start, 0.5)
        if a <= 0:
            continue
        (x0, y0), (x1, y1) = pos[a_], pos[b_]
        xe, ye = x0 + (x1 - x0) * a, y0 + (y1 - y0) * a
        d.line([(x0, y0), (xe, ye)], fill=th["muted"], width=6)
        if len(e) > 2 and e[2] and a >= 1:
            d.text(((x0 + x1) / 2, (y0 + y1) / 2 - 40), e[2], font=font("semi", int(h * 0.032)),
                   fill=th["muted"], anchor="mm")
    if data.get("pulse") and edges:
        chain = [pos[edges[0][0]]] + [pos[e[1]] for e in edges]
        t0 = 0.2 + len(nodes) * step
        if t > t0:
            period = max(1.5, data.get("pulse_period", 2.5))
            ph = ((t - t0) % period) / period
            p = _partial(chain, ph)[-1]
            for rr, al in ((34, 0.25), (22, 0.5), (12, 1)):
                d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=mix(th["bg"], th["accent"], al))
    for i, n in enumerate(nodes):
        a = prog(t, 0.2 + i * step, 0.45)
        if a <= 0:
            continue
        x, y = pos[n["id"]]
        f = font("bold", int(h * 0.036))
        lines = wrap(d, n["label"], f, w * 0.16)
        bw = max(text_w(d, l, f) for l in lines) + 60
        bh = len(lines) * int(h * 0.045) + 44
        s = 0.9 + 0.1 * a
        col = th.get(n.get("color", "panel"), th["panel"])
        rrect(d, [x - bw / 2 * s, y - bh / 2 * s, x + bw / 2 * s, y + bh / 2 * s], 18,
              fill=mix(th["bg"], col, a), outline=mix(th["bg"], th["accent"], a), width=3)
        ty = y - (len(lines) - 1) * h * 0.0225
        for l in lines:
            d.text((x, ty), l, font=f, fill=mix(th["bg"], th["text"], a), anchor="mm")
            ty += h * 0.045
    if data.get("title"):
        d.text((w / 2, h * 0.14), data["title"].upper(), font=font("display", int(h * 0.065)),
               fill=mix(th["bg"], th["text"], prog(t, 0, 0.4)), anchor="mm")


def s_scale(c, t, dur, data, th):
    """Comparación de tamaños: círculos o barras verticales que crecen, con etiquetas."""
    d = ImageDraw.Draw(c)
    w, h = c.size
    items = data["items"]  # {label, size (relativo), sub}
    smax = max(i["size"] for i in items)
    n = len(items)
    base_y = h * 0.78
    for k, it in enumerate(items):
        a = prog(t, 0.2 + k * 0.5, 0.7)
        cx = w * (k + 1) / (n + 1)
        r = max(4, (h * 0.26) * math.sqrt(it["size"] / smax)) * a
        col = th["accent"] if k == data.get("highlight", n - 1) else th["text"]
        d.ellipse([cx - r, base_y - 2 * r, cx + r, base_y], fill=mix(th["bg"], col, a))
        d.text((cx, base_y + 50), it["label"], font=font("bold", int(h * 0.04)),
               fill=mix(th["bg"], th["text"], a), anchor="mm")
        if it.get("sub"):
            d.text((cx, base_y + 100), it["sub"], font=font("semi", int(h * 0.03)),
                   fill=mix(th["bg"], th["muted"], a), anchor="mm")
    if data.get("title"):
        f = fit_font(d, data["title"].upper(), "display", w * 0.85, 1, int(h * 0.07))
        d.text((w / 2, h * 0.14), data["title"].upper(), font=f,
               fill=mix(th["bg"], th["text"], prog(t, 0, 0.4)), anchor="mm")


SCENES.update({
    "map_route": s_map_route,
    "cross_section": s_cross_section,
    "diagram": s_diagram,
    "scale": s_scale,
})


# ───────────────────────── aviación: avión, altitud y gráficas múltiples ─────────────────────────

def plane(d, x, y, s, color, angle=0.0):
    """Silueta de avión comercial vista desde el lado (morro a la derecha), centrada en (x, y), largo s."""
    pts_body = [(-0.5, -0.035), (0.36, -0.045), (0.46, -0.03), (0.5, 0.0), (0.46, 0.03), (0.36, 0.045),
                (-0.42, 0.045), (-0.5, 0.02)]
    tail = [(-0.5, -0.03), (-0.44, -0.03), (-0.34, -0.035), (-0.44, -0.2), (-0.5, -0.2)]
    wing = [(0.05, 0.02), (-0.14, 0.02), (-0.27, 0.16), (-0.2, 0.16)]
    stab = [(-0.36, 0.0), (-0.46, 0.0), (-0.52, 0.07), (-0.47, 0.07)]
    engine = [(-0.02, 0.07), (-0.16, 0.07), (-0.16, 0.115), (-0.02, 0.115)]
    ca, sa = math.cos(angle), math.sin(angle)

    def T(pts):
        return [(x + (px * ca - py * sa) * s, y + (px * sa + py * ca) * s) for px, py in pts]

    for poly in (tail, stab, pts_body, wing, engine):
        d.polygon(T(poly), fill=color)
    for k in range(9):  # ventanillas
        wx = 0.3 - k * 0.07
        d.ellipse([T([(wx, -0.012)])[0][0] - s * .008, T([(wx, -0.012)])[0][1] - s * .008,
                   T([(wx, -0.012)])[0][0] + s * .008, T([(wx, -0.012)])[0][1] + s * .008], fill=(20, 30, 50))


def s_altitude(c, t, dur, data, th):
    """Regla vertical de altitud con marcas (Everest, nubes…) y un avión que sube hasta `target`."""
    d = ImageDraw.Draw(c)
    w, h = c.size
    marks = data.get("marks", [])  # {alt, label, color?}
    top = data.get("max", 20000)
    target = data.get("target", 10700)
    x_axis = w * 0.22
    y0, y1 = h * 0.9, h * 0.12

    def Y(alt):
        return y0 - (alt / top) * (y0 - y1)

    # capas de fondo opcionales (bandas: nubes, tropopausa…)
    for band in data.get("bands", []):
        a = prog(t, 0.2, 0.6)
        col = mix(th["bg"], th.get(band.get("color", "panel"), th["panel"]), 0.55 * a)
        d.rectangle([x_axis, Y(band["to"]), w * 0.97, Y(band["from"])], fill=col)
        d.text((w * 0.95, Y(band["to"]) + 16), band["label"].upper(), font=font("semi", int(h * 0.026)),
               fill=mix(th["bg"], th["muted"], a), anchor="rt")
    d.line([(x_axis, y0), (x_axis, y1)], fill=th["muted"], width=4)
    f_t = font("semi", int(h * 0.028))
    step = data.get("tick", 5000)
    for alt in range(0, int(top) + 1, int(step)):
        d.line([(x_axis - 16, Y(alt)), (x_axis, Y(alt))], fill=th["muted"], width=3)
        d.text((x_axis - 26, Y(alt)), data.get("tick_fmt", "{:,} m").format(alt), font=f_t, fill=th["muted"],
               anchor="rm")
    for i, m in enumerate(marks):
        a = prog(t, 0.3 + i * 0.35, 0.5)
        if a <= 0:
            continue
        y = Y(m["alt"])
        col = th.get(m.get("color", "text"), th["text"])
        if m.get("shape") == "mountain":
            base = w * 0.34
            d.polygon([(base - 170, y0), (base, y0 - (y0 - y) * a), (base + 170, y0)], fill=mix(th["bg"], col, a * .6))
        d.line([(x_axis, y), (x_axis + (w * 0.72) * a, y)], fill=mix(th["bg"], col, 0.5 * a), width=2)
        d.text((x_axis + 24, y - 10), m["label"], font=font("bold", int(h * 0.034)), fill=mix(th["bg"], col, a),
               anchor="ls")
    pa = prog(t, 0.4, max(1.2, dur * 0.45))
    alt_now = target * pa
    px = w * 0.62 + 0.0
    py = Y(alt_now)
    plane(d, px, py, w * 0.2, th["accent"], angle=-0.12 * (1 - pa))
    f_v = font("display", int(h * 0.07))
    d.text((px, py - h * 0.075), data.get("value_fmt", "{:,.0f} m").format(alt_now), font=f_v, fill=th["text"],
           anchor="mm", stroke_width=5, stroke_fill=th["bg"])
    if data.get("title"):
        d.text((w * 0.6, h * 0.07), data["title"].upper(), font=font("display", int(h * 0.055)),
               fill=mix(th["bg"], th["text"], prog(t, 0, 0.4)), anchor="mm")


def s_multi_line(c, t, dur, data, th):
    """Varias series en una gráfica (p. ej., velocidad mínima y máxima que se juntan)."""
    d = ImageDraw.Draw(c)
    w, h = c.size
    series = data["series"]  # {points:[[x,y]], color, label}
    allx = [p[0] for s_ in series for p in s_["points"]]
    ally = [p[1] for s_ in series for p in s_["points"]]
    xmin, xmax = data.get("xmin", min(allx)), data.get("xmax", max(allx))
    ymin, ymax = data.get("ymin", 0), data.get("ymax", max(ally) * 1.1)
    x0, x1, y0, y1 = w * 0.14, w * 0.9, h * 0.72, h * 0.24

    def P(p):
        return (x0 + (p[0] - xmin) / ((xmax - xmin) or 1) * (x1 - x0), y0 - (p[1] - ymin) / ((ymax - ymin) or 1) * (y0 - y1))

    d.line([(x0, y0), (x1, y0)], fill=th["muted"], width=3)
    d.line([(x0, y0), (x0, y1)], fill=th["muted"], width=3)
    if data.get("xlabel"):
        d.text(((x0 + x1) / 2, y0 + 60), data["xlabel"], font=font("semi", int(h * 0.032)), fill=th["muted"], anchor="mm")
    if data.get("ylabel"):
        d.text((x0 - 20, y1 - 30), data["ylabel"], font=font("semi", int(h * 0.032)), fill=th["muted"], anchor="lm")
    for i, s_ in enumerate(series):
        a = prog(t, 0.3 + i * 0.6, max(1.2, dur * 0.4))
        pts = _partial([P(p) for p in s_["points"]], a)
        col = th.get(s_.get("color", "accent"), th["accent"])
        if len(pts) > 1:
            d.line(pts, fill=col, width=8, joint="curve")
            ex, ey = pts[-1]
            d.ellipse([ex - 12, ey - 12, ex + 12, ey + 12], fill=col)
            if a > 0.9 and s_.get("label"):
                d.text((ex + 20, ey), s_["label"], font=font("bold", int(h * 0.034)), fill=col, anchor="lm")
    zone = data.get("zone")  # {x, label}
    if zone and t > 0.3 + len(series) * 0.6 + 1.2:
        za = prog(t, 0.3 + len(series) * 0.6 + 1.2, 0.5)
        zx, zy = P((zone["x"], zone.get("y", (ymin + ymax) / 2)))
        r = 70 * za
        d.ellipse([zx - r, zy - r, zx + r, zy + r], outline=th["red"], width=8)
        d.text((zx, zy - 110), zone["label"].upper(), font=font("display", int(h * 0.05)), fill=th["red"], anchor="mm",
               stroke_width=4, stroke_fill=th["bg"])
    if data.get("title"):
        f = fit_font(d, data["title"].upper(), "display", w * 0.8, 1, int(h * 0.065))
        d.text((w / 2, h * 0.13), data["title"].upper(), font=f, fill=mix(th["bg"], th["text"], prog(t, 0, .4)),
               anchor="mm")


SCENES.update({"altitude": s_altitude, "multi_line": s_multi_line})

"""Convierte guiones escritos en texto simple (guiones/<canal>/*.txt) al JSON que usa el sistema.

Formato del .txt:
    title: ...            (y topic, thumbnail_text, thumbnail_highlight, pinned_comment)
    alt_titles: a || b
    tags: a, b, c
    hashtags: #a #b #c
    check: dato 1 || dato 2
    description:
    varias líneas...
    === SEGMENTS
    > búsqueda uno | búsqueda dos
    texto narrado...
    === SHORT
    title: ...
    description: ...
    > búsqueda | búsqueda
    texto...

Uso: python scripts/txt_a_json.py guiones/en/001_blockbuster.txt [...]
"""
import json
import sys
from pathlib import Path


def parse_segments(lines):
    segs, cur = [], None
    for line in lines:
        if line.startswith(">"):
            cur = {"broll": [q.strip() for q in line[1:].split("|") if q.strip()], "text": ""}
            segs.append(cur)
        elif line.strip() and cur is not None:
            cur["text"] = (cur["text"] + " " + line.strip()).strip()
    return segs


def parse(path: Path) -> dict:
    text = path.read_text("utf-8")
    head, rest = text.split("=== SEGMENTS", 1)
    body, short = rest.split("=== SHORT", 1) if "=== SHORT" in rest else (rest, "")
    pkg, desc, in_desc = {}, [], False
    for line in head.splitlines():
        if in_desc:
            desc.append(line)
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key == "description":
            in_desc = True
        elif key in ("alt_titles", "check"):
            pkg["sources_to_check" if key == "check" else key] = [v.strip() for v in val.split("||")]
        elif key == "tags":
            pkg["tags"] = [t.strip() for t in val.split(",") if t.strip()]
        elif key == "hashtags":
            pkg["hashtags"] = val.split()
        elif key:
            pkg[key] = val
    pkg["description"] = "\n".join(desc).strip()
    pkg["segments"] = parse_segments(body.splitlines())
    if short.strip():
        s_lines = short.strip().splitlines()
        sh = {}
        for line in s_lines:
            k, _, v = line.partition(":")
            if k.strip() in ("title", "description") and not line.startswith(">"):
                sh[k.strip()] = v.strip()
        sh["segments"] = parse_segments(s_lines)
        pkg["short"] = sh
    return pkg


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        src = Path(arg)
        pkg = parse(src)
        words = sum(len(s["text"].split()) for s in pkg["segments"])
        swords = sum(len(s["text"].split()) for s in pkg.get("short", {}).get("segments", []))
        src.with_suffix(".json").write_text(json.dumps(pkg, ensure_ascii=False, indent=2), "utf-8")
        print(f"{src.name}: {len(pkg['segments'])} segmentos, {words} palabras, short {swords} palabras")

"""Comprueba que un guion animado está completo y bien formado antes de producirlo.

Uso: python scripts/validar_guion.py guiones/atlas/002_xxx.py
Genera el .json (ejecutando el .py) y revisa estructura, duración, miniaturas y Shorts.
Sale con código 1 y explica qué falla si algo no cumple.
"""
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from yt.anim.scenes import SCENES  # noqa: E402

MIN_WORDS, MAX_WORDS = 2250, 3200  # ≈ 15-20 min con la voz del canal


def main(path: Path) -> int:
    runpy.run_path(str(path), run_name="__main__")
    data = json.loads(path.with_suffix(".json").read_text("utf-8"))
    errors = []
    for key in ("videoId", "channel", "title", "metadata", "chapters"):
        if key not in data:
            errors.append(f"falta '{key}'")
    md = data.get("metadata", {})
    for key in ("description", "tags", "thumbnails", "alt_titles", "pinned_comment"):
        if not md.get(key):
            errors.append(f"falta metadata.{key}")
    if len(md.get("thumbnails", [])) != 3:
        errors.append("tiene que haber exactamente 3 miniaturas")
    for t in md.get("thumbnails", []):
        if not t.get("prompt") or not t.get("text"):
            errors.append("cada miniatura necesita 'prompt' (foto realista) y 'text'")
    if len(data.get("title", "")) > 70:
        errors.append("título de más de 70 caracteres")
    scenes = [s for c in data.get("chapters", []) for s in c["scenes"]]
    words = sum(len(s.get("narration", "").split()) for s in scenes)
    if not MIN_WORDS <= words <= MAX_WORDS:
        errors.append(f"la narración tiene {words} palabras (debe estar entre {MIN_WORDS} y {MAX_WORDS})")
    shorts = data.get("shorts", [])
    if len(shorts) != 3:
        errors.append("tiene que haber exactamente 3 Shorts")
    for sc in scenes + [s for sh in shorts for s in sh.get("scenes", [])]:
        if sc.get("type") not in SCENES:
            errors.append(f"tipo de escena desconocido: {sc.get('type')}")
        if sc.get("type") != "end_screen" and not sc.get("narration"):
            errors.append(f"escena sin narración: {sc.get('type')}")
    if scenes and scenes[-1].get("type") != "end_screen":
        errors.append("la última escena debe ser end_screen")
    elif scenes and scenes[-1].get("data", {}).get("next_title"):
        errors.append("la pantalla final no debe anunciar otro vídeo (quita next_title): solo suscripción")
    long_scenes = [s for s in scenes if len(s.get("narration", "").split()) > 55]
    if long_scenes:
        errors.append(f"{len(long_scenes)} escenas con más de 55 palabras (divídelas: un cambio visual cada 5-15 s)")
    if errors:
        print("✘ El guion no es válido:\n  - " + "\n  - ".join(errors))
        return 1
    print(f"✔ Guion válido: {len(scenes)} escenas, {words} palabras, {len(shorts)} Shorts")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))

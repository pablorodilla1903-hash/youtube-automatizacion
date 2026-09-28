"""Sube una carpeta local (con subcarpetas) a Google Drive, dentro de "YouTube Automático/".

Uso: python scripts/subir_a_drive.py <carpeta>
No vuelve a subir los archivos que ya están (por nombre), así que se puede repetir sin duplicar nada.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from yt import drive  # noqa: E402


def main(base: Path) -> None:
    if not drive.Drive.configured():
        sys.exit("✘ Faltan los secretos de Google Drive (GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN)")
    folders = sorted({p.parent for p in base.rglob("*") if p.is_file() and ".git" not in p.parts and p.name != "README.md"})
    for folder in folders:
        remote = list(folder.relative_to(base).parts)
        drive.upload_folder(folder, remote, skip_existing=True)
    print("✔ Todo subido a Google Drive → YouTube Automático/")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())

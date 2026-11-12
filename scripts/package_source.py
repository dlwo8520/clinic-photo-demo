"""Package only source allowlists, without runtime files, uploads or secrets."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent.parent
SOURCE_TREES = ("config", "clinic", "scripts", "ops")
SOURCE_FILES = ("manage.py", "requirements.txt", "README.md", "render.yaml", ".gitignore", ".gitattributes")


def main():
    output = ROOT / "artifacts" / "clinic-photo-demo-source.zip"
    output.parent.mkdir(exist_ok=True)
    files = [ROOT / name for name in SOURCE_FILES]
    for name in SOURCE_TREES:
        files.extend(p for p in (ROOT / name).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"})
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"Source archive: {output} ({len(files)} files)")


if __name__ == "__main__":
    main()

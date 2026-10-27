"""Write data/raw/MANIFEST.md5 (``md5sum -c`` format) for every file under data/raw.

Run before uploading the dataset to Zenodo; ``scripts/download_data.py`` and notebook 00 check it.
"""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "raw"


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name not in ("MANIFEST.md5", ".DS_Store"))
    lines = [f"{md5(p)}  {p.relative_to(ROOT).as_posix()}" for p in files]
    (ROOT / "MANIFEST.md5").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(lines)} entries to {ROOT / 'MANIFEST.md5'}")


if __name__ == "__main__":
    main()

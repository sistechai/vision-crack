"""Download the VisionCrack dataset from Zenodo into data/raw and verify MANIFEST.md5.

Usage:  python scripts/download_data.py
"""

import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

# TODO(release): fill in after the Zenodo upload (record id and file name of the zip).
ZENODO_RECORD = None            # e.g. "1234567"
ARCHIVE = "visioncrack_data_v1.zip"

ROOT = Path(__file__).resolve().parents[1] / "data" / "raw"


def verify(root: Path = ROOT) -> bool:
    manifest = root / "MANIFEST.md5"
    if not manifest.exists():
        print("no MANIFEST.md5 found; cannot verify")
        return False
    bad = 0
    for line in manifest.read_text().splitlines():
        digest, rel = line.split("  ", 1)
        p = root / rel
        if not p.exists() or hashlib.md5(p.read_bytes()).hexdigest() != digest:
            print("MISMATCH", rel)
            bad += 1
    print("all files verified" if not bad else f"{bad} files missing or changed")
    return bad == 0


def main() -> None:
    if ZENODO_RECORD is None:
        sys.exit("Dataset DOI not set yet. Put the data under data/raw/ manually (see data/README.md).")
    ROOT.mkdir(parents=True, exist_ok=True)
    url = f"https://zenodo.org/records/{ZENODO_RECORD}/files/{ARCHIVE}?download=1"
    zip_path = ROOT.parent / ARCHIVE
    print("downloading", url)
    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(ROOT)
    zip_path.unlink()
    sys.exit(0 if verify() else 1)


if __name__ == "__main__":
    main()

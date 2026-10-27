"""Build the Zenodo upload: data/visioncrack_data_v1.zip (data/raw + licence), with a fresh MANIFEST.md5.

After uploading, put the record id into scripts/download_data.py (ZENODO_RECORD).
"""

import zipfile

from make_manifest import ROOT, main as make_manifest

REPO = ROOT.parents[1]
OUT = REPO / "data" / "visioncrack_data_v1.zip"


def main() -> None:
    make_manifest()
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name != ".DS_Store")
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_STORED) as z:     # images are already compressed
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
        z.write(REPO / "LICENSE-DATA", "LICENSE")
        z.write(REPO / "data" / "README.md", "README.md")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.0f} MB, {len(files) + 2} files)")


if __name__ == "__main__":
    main()

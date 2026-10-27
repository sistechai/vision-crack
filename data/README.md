# Data

The full dataset (~155 MB) is hosted on Zenodo (**DOI: to be added**) under **CC-BY-4.0**.
Get it with `python scripts/download_data.py`, which unpacks into `data/raw/` and checks `MANIFEST.md5`.
`data/sample/` is a one-image subset kept in git for the tests and CI.

```
data/
├── raw/                         # from Zenodo (git-ignored)
│   ├── MANIFEST.md5
│   ├── table1_et/               # Table 1: printed targets ET-1..ET-5, label #26
│   │   ├── images/<unix-ts>.png     10 captures, 2160×3840, RGB
│   │   ├── metadata.csv             app-detected corners (ROI coordinates)
│   │   ├── inspectors.csv           10 inspectors × 5 targets, crack-gauge readings (mm)
│   │   └── README.md
│   └── robustness/              # revision sweep: label "#1" (code lewb), 45 handheld captures
│       ├── norm/  dist/  roll/  pitch/  yaw/    <unix-ts>_<a>_<b>_<c>.jpg, 3024×4032
│       └── metadata.csv
├── synthetic/pose_points.json   # synthetic label corners for rotation / pitch / yaw (notebook 03)
└── sample/                      # 1 Table 1 capture, for CI
```

## Capture devices and labels
| Set | Label | Code | Bar classes | Image size |
|---|---|---|---|---|
| `table1_et` | VisionCrack #26 | `3D6m` | 5 4 3 · 1 3 4 · 4 2 3 · 1 4 3 · 2 5 4 · 1 2 3 | 2160 × 3840 |
| `robustness` | Vision Crack #1 | `lewb` | 5 4 3 · 2 5 3 · 2 3 1 · 3 5 1 · 2 1 3 · 1 2 3 | 3024 × 4032 |

<!-- TODO(author): phone model(s) for each set. -->

Ground-truth widths of the printed targets: 0.55, 1.10, 1.65, 2.20, 2.75 mm (ET-1..ET-5).

## `table1_et/metadata.csv`
| Column | Meaning |
|---|---|
| `image` | file in `images/` (name = capture unix time) |
| `tl_x … br_y` | corners P1 (top-left), P2 (top-right), P3 (bottom-left), P4 (bottom-right) found by the app, in **ROI** pixels. Add the ROI origin (682, 2884) for image pixels |

## `robustness/metadata.csv`
| Column | Meaning |
|---|---|
| `folder` | condition: `norm` reference pose · `dist` farther · `roll` in-plane rotation · `pitch` / `yaw` out-of-plane tilt |
| `legacy_name` | folder name used in the original analysis (`angle` = now `roll`, `roll` = now `pitch`) |
| `file` | image file name |
| `pose_a, pose_b, pose_c` | the phone's orientation-sensor readings at capture (deg), from the file name. **Not** the label pose |
| `label_x, label_y, label_w, label_h` | hand-drawn box around the label (image pixels) |
| `et_x, et_y, et_w, et_h` | hand-drawn box around the five printed reference bars |

No image contains EXIF or GPS metadata (checked).
Not included: 4 extra captures (`1783296950…`, `1783297017…`, `1783297038…`, `1783297090…`) that are not part of any analysis.

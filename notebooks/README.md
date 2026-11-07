# Notebooks

Each notebook reproduces one part of the paper. They import the `visioncrack` package (`pip install -e .`),
read from `data/`, write to `results/`, and **assert** the published numbers where there are any.

| Notebook | Paper item | Checks against paper |
|---|---|---|
| `01_roi_and_capture_geometry` | Sec. 2.1.2, Eq. 1–5, Fig. image_capture | ROI = (682, 2884, 797, 478) |
| `02_barcode_detection_pipeline` | Sec. 2.2 Step 1, Fig. pipeline | Python port = phone corners (≤ 2 px) |
| `03_capture_gates` | Sec. 2.2 Steps 2–4, Figs. condition1–3, gate geometry | all Table 1 captures accepted |
| `04_crack_width_extraction` | Sec. 2.3, Fig. extraction, matrix M | — |
| `05_table1_inspectors_vs_visioncrack` | **Table 1**, Figs. ex21–ex23 | every Table 1 number, 63 % / 93 % |
| `06_robustness_sweep` | Sec. III-A: the 45 sensitivity captures, app gates and measurement chain | expected per-capture values |
| `07_acceptance_rate` | Supplementary: acceptance per condition from the measurement chain (the paper's Table 2 uses the app's own decision, notebook 14) | expected values |
| `08_error_model_tilt` | Sec. III-A: scale error 1/cos φ − 1, in-plane rotation, tilt from the four corners | 0.06 / 0.38 / 1.5 % |
| `09_uncertainty_and_bias` | Supplementary: U₉₅ per target, constant edge offset, sub-pixel edges | expected values |
| `10_field_crack_repeatability` | Real wall crack (repo only): 20 app captures → 10 selected by quality | — (new data, no reference width) |
| `11_field_crack_measurement` | Real crack (repo only): one measuring point (7–9 mm from the label frame), five options (middle row, median, mean, Table 1 rule > 2 px / > 6 px), step by step on photo 1, widths of all 10 photos | — |
| `12_field_crack_result` | Real crack (repo only): the five options vs. ruler GT (0.45 mm) in Table 1 layout; error in mm / % / px; compared with VisionCrack on the printed targets | Table 1 unchanged with the 2-px filter |
| `13_camera_app_vs_visioncrack` | Real crack (repo only): 21 photos from the phone's own camera app vs. the 10 app photos; app-gate check, five options at P3, spread / MDC, why (pixels on the crack, lens, rotation), common questions | — (label re-placed: GT indicative only) |
| `14_table2_and_checks` | **Table 2** with one scale and all 45 frames plus the app's accept/reject, homography-rectification baseline, re-acquisition of the Table 3 photos and why ET2 has SD = 0, ink spread and scale check, MDC 95 % CI, decode rate, per-row pixel counts | Table 2, Table 3, MDC |

Run them all headless:

```bash
bash scripts/run_all_notebooks.sh          # all notebooks, in order
bash scripts/run_all_notebooks.sh 13 14    # only some
```

Typical runtime is a few minutes in total.

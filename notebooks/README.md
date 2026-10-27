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
| `06_robustness_sweep` | Fig. robustness, cond_* | revision-experiment outputs |
| `07_acceptance_rate` | Table acceptance (R1.2) | revision draft table |
| `08_error_model_tilt` | Eq. tilt_error, tilt_fit (R1.4, R2.2) | 0.06 / 0.38 / 1.5 %; w₀, k, R², 14.3° |
| `09_uncertainty_and_bias` | Table uncertainty, small-width bias | revision draft table |

Run them all headless:

```bash
for nb in notebooks/0*.ipynb; do jupyter nbconvert --to notebook --execute "$nb" --inplace; done
```

Typical runtime is under 2 minutes in total.

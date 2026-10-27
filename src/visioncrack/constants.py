"""Constants from the paper. Section and equation numbers refer to the manuscript."""

# --- Label geometry (Sec. 2.1.1) ---
LABEL_WIDTH_MM = 50.0          # physical label width used as the scale reference (Sec. 2.3.2)
LABEL_HEIGHT_MM = 30.0
LABEL_ASPECT = 3 / 5           # h / w

# --- Guided capture ROI (Sec. 2.1.2, Eq. 1-5) ---
ROI_ALPHA = 0.45               # fraction of the preview width covered by the guide

# --- Capture gates (Sec. 2.2) ---
COVERAGE_MIN = 0.95            # tau_w = tau_h (Step 3)
ROTATION_MAX_DEG = 2.0         # tau_theta (Step 4)

# --- Bar / width extraction (Sec. 2.3.1) ---
GAUSSIAN_KSIZE = (3, 3)
GAUSSIAN_SIGMA = 2
MIN_RUN_PX = 6                 # dark runs this long or shorter are noise, not bars
CLIP_Z = 1.645                 # per-bar outlier clipping (90 % two-sided interval)

# Barcode crop inside the detected label (pixels, relative to the top-left corner)
BARCODE_MARGIN_X = 20          # left/right margin
BARCODE_MARGIN_Y_FRAC = 1 / 6  # top/bottom margin as a fraction of the ROI height

# Crack-target crop: a band above the barcode, in pixels from the barcode crop top
ET_BAND_TOP = 500
ET_BAND_BOTTOM = 200

# --- Experimental targets (Sec. 3) ---
ET_GT_MM = (0.55, 1.10, 1.65, 2.20, 2.75)
ET_LAYOUT = (5, 4, 1, 2, 3)    # which ET class each printed bar is, left to right
BARCODE_CLASS_MM = (0.5, 1.0, 1.5, 2.0, 2.5)
N_BARCODE_BARS = 18

// Paper constants and the capture guide (ROI).
// Python twin: src/visioncrack/constants.py and roi.py.
import 'dart:ui';

/// ROI width as a fraction of the screen width (paper Eq. 1).
const double kRoiAlpha = 0.45;

/// ROI aspect ratio height / width = 3 / 5, the label's 30 × 50 mm (Eq. 2).
const double kRoiAspect = 3 / 5;

/// Gate 2: each corner-to-corner distance must cover more than this share of the ROI side.
const double kCoverageMin = 0.95;

/// Gate 3: the label's left edge must be within this many degrees of vertical.
const double kRotationMaxDeg = 2.0;

/// Corner search: height (px) of the top and bottom bands searched for red blocks.
const int kBandHeight = 64;

/// Red block size (px). A block counts as red when at least 3 of its 4 pixels are red.
const int kBlockSize = 2;

/// A band with more red blocks than this is treated as "no label" (e.g. a red wall).
const int kMaxBlocks = 15000;

/// Detection runs on a copy of the ROI scaled to roughly this frame width (px).
const int kDetectionFrameWidth = 1920;

/// Extra app checks that the paper does not describe. They only wait for a sharper photo
/// (phone held still, focus/exposure locked) and do not change the geometry gates.
/// Set to false to capture as soon as the three paper gates pass.
const bool kUseStillnessAndFocusLock = true;
const double kStillnessThreshold = 0.20; // EWMA of |accel| − g, m/s²
const int kStillFramesRequired = 5;

/// JPEG quality of the saved capture.
const int kJpegQuality = 95;

/// The guide box on screen and in the camera frame. Both use the same formula:
///   w = α·W,  h = 3/5·w,  x = (W − w)/2,  y = H − 2h
class Roi {
  final double x, y, w, h;
  const Roi(this.x, this.y, this.w, this.h);

  Rect get rect => Rect.fromLTWH(x, y, w, h);

  /// ROI on the screen (logical pixels).
  factory Roi.onScreen(Size screen) {
    final w = screen.width * kRoiAlpha;
    final h = kRoiAspect * w;
    return Roi((screen.width - w) / 2, screen.height - 2 * h, w, h);
  }

  /// The same ROI in an upright camera frame. The preview fills the screen height,
  /// so the screen-to-image scale is image height / screen height (paper Eq. 3–5).
  static List<int> inImage(Size screen, Size image) {
    final w = (image.height * screen.width * kRoiAlpha / screen.height).round();
    final h = (kRoiAspect * w).round();
    final x = ((image.width - w) / 2).round();
    final y = (image.height - 2 * h).round();
    return [x, y, w, h];
  }
}

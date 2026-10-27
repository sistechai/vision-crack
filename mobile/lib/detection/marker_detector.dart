// Label corner detection and the three capture gates (paper Sec. 2, Figs. condition 1–3).
// Pure Dart (no Flutter), so it runs in an isolate and in `flutter test`.
// Python twin: src/visioncrack/detection.py and gates.py.
import 'dart:math' as math;

import 'package:image/image.dart' as img;

import '../config.dart';

/// Result for one ROI crop. Corners are in ROI pixels: [x, y].
class Detection {
  final List<int>? tl, tr, bl, br;

  /// Coverage ratios d1/w, d2/h, d3/w, d4/h (top, right, bottom, left).
  final List<double>? ratios;

  /// Rotation of the left edge from vertical, degrees.
  final double? angleDeg;

  /// Name of the first gate that failed: 'corners', 'coverage' or 'rotation'. Null if accepted.
  final String? failure;

  const Detection({this.tl, this.tr, this.bl, this.br, this.ratios, this.angleDeg, this.failure});

  bool get accepted => failure == null;

  List<List<int>>? get corners => tl == null ? null : [tl!, tr!, bl!, br!];

  Detection scaled(int f) {
    List<int>? s(List<int>? p) => p == null ? null : [p[0] * f, p[1] * f];
    return Detection(
        tl: s(tl), tr: s(tr), bl: s(bl), br: s(br), ratios: ratios, angleDeg: angleDeg, failure: failure);
  }

  Map<String, dynamic> toJson() => {
        'corners_roi_px': {'tl': tl, 'tr': tr, 'bl': bl, 'br': br},
        'coverage': ratios,
        'angle_deg': angleDeg,
        'accepted': accepted,
      };
}

/// HSV in OpenCV units (H 0–180, S and V 0–255): red, if both ranges are met.
bool isRed(int r, int g, int b) {
  final mx = math.max(r, math.max(g, b));
  final mn = math.min(r, math.min(g, b));
  final delta = mx - mn;
  if (mx < 100 || delta == 0) return false; // V >= 100
  if (delta * 255 < 100 * mx) return false; // S >= 100
  double h;
  if (mx == r) {
    h = 60 * (((g - b) / delta) % 6);
  } else if (mx == g) {
    h = 60 * ((b - r) / delta + 2);
  } else {
    h = 60 * ((r - g) / delta + 4);
  }
  if (h < 0) h += 360;
  h /= 2;
  return h <= 10 || h >= 160;
}

/// Centres of all 2×2 windows (stride 1) with at least 3 red pixels, in band coordinates.
List<List<int>> redBlocks(img.Image image, int y0, int bandH) {
  final w = image.width;
  final red = List.generate(bandH, (_) => List<bool>.filled(w, false));
  for (var y = 0; y < bandH; y++) {
    for (var x = 0; x < w; x++) {
      final p = image.getPixel(x, y0 + y);
      red[y][x] = isRed(p.r.toInt(), p.g.toInt(), p.b.toInt());
    }
  }
  final blocks = <List<int>>[];
  final need = kBlockSize * kBlockSize ~/ 2; // count must be > 2, i.e. >= 3 of 4
  for (var i = 0; i <= bandH - kBlockSize; i++) {
    for (var j = 0; j <= w - kBlockSize; j++) {
      var count = 0;
      for (var dy = 0; dy < kBlockSize; dy++) {
        for (var dx = 0; dx < kBlockSize; dx++) {
          if (red[i + dy][j + dx]) count++;
        }
      }
      if (count > need) blocks.add([j + kBlockSize ~/ 2, i + kBlockSize ~/ 2]);
    }
  }
  return blocks;
}

List<int> _closest(List<List<int>> pts, int rx, int ry) {
  var best = pts.first;
  var bestD = double.infinity;
  for (final p in pts) {
    final d = math.pow(p[0] - rx, 2) + math.pow(p[1] - ry, 2);
    if (d < bestD) {
      bestD = d.toDouble();
      best = p;
    }
  }
  return best;
}

/// Finds the label corners in an ROI crop and applies the three gates.
Detection detect(img.Image roi) {
  final w = roi.width, h = roi.height;
  final band = math.min(kBandHeight, h);

  // Gate 1: red blocks near all four ROI corners.
  final top = redBlocks(roi, 0, band);
  final bottom = redBlocks(roi, h - band, band);
  if (top.isEmpty || bottom.isEmpty || top.length > kMaxBlocks || bottom.length > kMaxBlocks) {
    return const Detection(failure: 'corners');
  }
  final tl = _closest(top, 0, 0);
  final tr = _closest(top, w, 0);
  final blBand = _closest(bottom, 0, band);
  final brBand = _closest(bottom, w, band);
  final bl = [blBand[0], blBand[1] + h - band];
  final br = [brBand[0], brBand[1] + h - band];

  // Gate 2: the label fills the ROI.
  double r(num v) => (v * 1000).round() / 1000;
  final ratios = [
    r((tr[0] - tl[0]).abs() / w),
    r((br[1] - tr[1]).abs() / h),
    r((br[0] - bl[0]).abs() / w),
    r((bl[1] - tl[1]).abs() / h),
  ];
  final raw = [
    (tr[0] - tl[0]).abs() / w,
    (br[1] - tr[1]).abs() / h,
    (br[0] - bl[0]).abs() / w,
    (bl[1] - tl[1]).abs() / h,
  ];
  if (raw.any((v) => v <= kCoverageMin)) {
    return Detection(tl: tl, tr: tr, bl: bl, br: br, ratios: ratios, failure: 'coverage');
  }

  // Gate 3: the label is upright.
  final angle = 90 - math.atan2(bl[1] - tl[1], bl[0] - tl[0]) * 180 / math.pi;
  return Detection(
      tl: tl,
      tr: tr,
      bl: bl,
      br: br,
      ratios: ratios,
      angleDeg: angle,
      failure: angle.abs() < kRotationMaxDeg ? null : 'rotation');
}

/// Short instruction for the user, from the smallest coverage ratio.
String? hintFor(Detection d) {
  if (d.ratios == null) return 'Fit the label in the box';
  final m = d.ratios!.reduce(math.min);
  if (m < 0.7) return 'Move closer';
  if (m > 1.05) return 'Move back';
  if (m <= kCoverageMin) return 'Almost there';
  if (d.failure == 'rotation') return 'Straighten the phone';
  return 'Hold steady';
}

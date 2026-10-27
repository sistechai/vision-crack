// Camera frame → RGB, in upright (portrait) coordinates.
//
// Android delivers sensor-oriented (landscape) frames; iOS delivers frames that are already
// portrait. [quarterTurns] maps upright pixel (x, y) to the sensor buffer, so the ROI and the
// saved photo are portrait on both platforms.
//
// The UI thread only copies bytes ([sampleFrame]); the colour maths runs in an isolate
// ([samplesToImage]) so the preview does not stutter.
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;

/// A downsampled crop of a frame, as raw bytes. format 0 = Y/U/V planes, 1 = packed RGB.
class FrameSamples {
  final int width, height, format;
  final Uint8List a;
  final Uint8List? u, v;
  const FrameSamples(this.width, this.height, this.format, this.a, [this.u, this.v]);
}

/// Clockwise quarter turns from the sensor buffer to the upright image (0 or 1 or 3).
int quarterTurnsFor(CameraImage f, int sensorOrientation) {
  if (f.width <= f.height) return 0; // already portrait (iOS)
  return sensorOrientation == 270 ? 3 : 1;
}

/// Size of the upright frame.
(int, int) uprightSize(CameraImage f, int turns) => turns == 0 ? (f.width, f.height) : (f.height, f.width);

/// Copies the upright rectangle (x, y, w, h), keeping every [step]-th pixel.
FrameSamples? sampleFrame(CameraImage f, int turns, int x, int y, int w, int h, {int step = 1}) {
  final (uw, uh) = uprightSize(f, turns);
  x = x.clamp(0, uw - 1);
  y = y.clamp(0, uh - 1);
  w = w.clamp(1, uw - x);
  h = h.clamp(1, uh - y);
  step = step < 1 ? 1 : step;
  final ow = w ~/ step, oh = h ~/ step, n = ow * oh;

  // Upright (ux, uy) → sensor (sx, sy).
  final sw = f.width, sh = f.height;
  int sxOf(int ux, int uy) => turns == 0 ? ux : (turns == 1 ? uy : sw - 1 - uy);
  int syOf(int ux, int uy) => turns == 0 ? uy : (turns == 1 ? sh - 1 - ux : ux);

  switch (f.format.group) {
    case ImageFormatGroup.yuv420:
      final yRow = f.planes[0].bytesPerRow;
      final uvRow = f.planes[1].bytesPerRow;
      final uvPix = f.planes[1].bytesPerPixel ?? 1;
      final yp = f.planes[0].bytes, up = f.planes[1].bytes, vp = f.planes[2].bytes;
      final yy = Uint8List(n), uu = Uint8List(n), vv = Uint8List(n);
      var k = 0;
      for (var j = 0; j < oh; j++) {
        final uy = y + j * step;
        for (var i = 0; i < ow; i++) {
          final ux = x + i * step;
          final sx = sxOf(ux, uy), sy = syOf(ux, uy);
          final uv = (sy >> 1) * uvRow + (sx >> 1) * uvPix;
          yy[k] = yp[sy * yRow + sx];
          uu[k] = up[uv];
          vv[k] = vp[uv];
          k++;
        }
      }
      return FrameSamples(ow, oh, 0, yy, uu, vv);
    case ImageFormatGroup.nv21:
      final yp = f.planes[0].bytes;
      final yRow = f.planes[0].bytesPerRow;
      final vu = f.planes.length > 1 ? f.planes[1].bytes : yp;
      final vuOffset = f.planes.length > 1 ? 0 : sh * yRow;
      final yy = Uint8List(n), uu = Uint8List(n), vv = Uint8List(n);
      var k = 0;
      for (var j = 0; j < oh; j++) {
        final uy = y + j * step;
        for (var i = 0; i < ow; i++) {
          final ux = x + i * step;
          final sx = sxOf(ux, uy), sy = syOf(ux, uy);
          final p = vuOffset + (sy >> 1) * yRow + (sx & ~1);
          yy[k] = yp[sy * yRow + sx];
          vv[k] = vu[p];
          uu[k] = vu[p + 1];
          k++;
        }
      }
      return FrameSamples(ow, oh, 0, yy, uu, vv);
    case ImageFormatGroup.bgra8888:
      final b = f.planes[0].bytes;
      final row = f.planes[0].bytesPerRow;
      final rgb = Uint8List(n * 3);
      var k = 0;
      for (var j = 0; j < oh; j++) {
        final uy = y + j * step;
        for (var i = 0; i < ow; i++) {
          final ux = x + i * step;
          final p = syOf(ux, uy) * row + sxOf(ux, uy) * 4;
          rgb[k] = b[p + 2];
          rgb[k + 1] = b[p + 1];
          rgb[k + 2] = b[p];
          k += 3;
        }
      }
      return FrameSamples(ow, oh, 1, rgb);
    default:
      return null;
  }
}

/// Samples → RGB image (BT.601 full-range YUV → RGB). Runs in an isolate.
img.Image samplesToImage(FrameSamples s) {
  final out = img.Image(width: s.width, height: s.height);
  var k = 0;
  for (var j = 0; j < s.height; j++) {
    for (var i = 0; i < s.width; i++) {
      if (s.format == 1) {
        out.setPixelRgb(i, j, s.a[k * 3], s.a[k * 3 + 1], s.a[k * 3 + 2]);
      } else {
        final yv = s.a[k], u = s.u![k] - 128, v = s.v![k] - 128;
        out.setPixelRgb(
          i,
          j,
          (yv + 1.402 * v).round().clamp(0, 255),
          (yv - 0.344136 * u - 0.714136 * v).round().clamp(0, 255),
          (yv + 1.772 * u).round().clamp(0, 255),
        );
      }
      k++;
    }
  }
  return out;
}

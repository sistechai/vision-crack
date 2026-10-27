// Same checks as the Python tests: the Dart detector must find the corners the phone
// recorded for the sample capture (data/sample), and the ROI must match roi.py.
import 'dart:io';
import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:visioncrack_capture/config.dart';
import 'package:visioncrack_capture/detection/marker_detector.dart';

const _sample = '../data/sample/table1_et/images/1752392841.png';

void main() {
  test('ROI in the image matches the paper / roi.py (682, 2884, 797, 478)', () {
    expect(Roi.inImage(const Size(430, 932), const Size(2160, 3840)), [682, 2884, 797, 478]);
  });

  group('sample capture', () {
    late img.Image roi;
    setUpAll(() {
      final full = img.decodePng(File(_sample).readAsBytesSync())!;
      roi = img.copyCrop(full, x: 682, y: 2884, width: 797, height: 478);
    });

    test('corners match the phone-recorded bbox within 2 px, and all gates pass', () {
      final d = detect(roi);
      // data/sample/table1_et/metadata.csv
      const expected = [[1, 3], [783, 17], [1, 477], [782, 477]];
      for (var i = 0; i < 4; i++) {
        expect((d.corners![i][0] - expected[i][0]).abs(), lessThanOrEqualTo(2), reason: 'corner $i x');
        expect((d.corners![i][1] - expected[i][1]).abs(), lessThanOrEqualTo(2), reason: 'corner $i y');
      }
      expect(d.accepted, isTrue, reason: 'failed: ${d.failure}');
      expect(d.angleDeg!.abs(), lessThan(kRotationMaxDeg));
    });

    test('label moved down out of the box: no corners in the top band', () {
      final shifted = img.Image(width: roi.width, height: roi.height);
      img.fill(shifted, color: img.ColorRgb8(255, 255, 255));
      img.compositeImage(shifted, roi, dstY: 120);
      expect(detect(shifted).failure, 'corners');
    });

    test('camera too far (label at 90 %) fails the coverage gate', () {
      final small = img.copyResize(roi, width: (roi.width * .9).round(), height: (roi.height * .9).round());
      final canvas = img.Image(width: roi.width, height: roi.height);
      img.fill(canvas, color: img.ColorRgb8(255, 255, 255));
      img.compositeImage(canvas, small, dstX: (roi.width - small.width) ~/ 2, dstY: (roi.height - small.height) ~/ 2);
      final d = detect(canvas);
      expect(d.failure, 'coverage');
    });

    test('rotated 4° fails the rotation gate', () {
      final full = img.decodePng(File(_sample).readAsBytesSync())!;
      final big = img.copyCrop(full, x: 682 - 200, y: 2884 - 200, width: 797 + 400, height: 478 + 400);
      final rot = img.copyRotate(big, angle: 4, interpolation: img.Interpolation.linear);
      final cx = rot.width ~/ 2, cy = rot.height ~/ 2;
      final crop = img.copyCrop(rot, x: cx - 797 ~/ 2, y: cy - 478 ~/ 2, width: 797, height: 478);
      final d = detect(crop);
      expect(d.accepted, isFalse);
    });

    test('a frame with no label fails the corners gate', () {
      final blank = img.Image(width: 797, height: 478);
      img.fill(blank, color: img.ColorRgb8(200, 200, 200));
      expect(detect(blank).failure, 'corners');
    });
  });
}

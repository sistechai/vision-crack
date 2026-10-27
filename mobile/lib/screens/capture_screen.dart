// Guided capture: live preview + guide box. The photo is taken automatically when the
// three paper gates pass (corners found, label fills the box, label upright).
// Pops with the saved Capture, or null if the user went back.
import 'dart:async';
import 'dart:io';
import 'dart:isolate';
import 'dart:math' as math;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;
import 'package:sensors_plus/sensors_plus.dart';

import '../camera/frame.dart';
import '../config.dart';
import '../detection/marker_detector.dart';
import '../storage/capture_store.dart';

// Top-level so the isolate closures capture only their argument, not the screen state.
Future<Detection> _detectInIsolate(FrameSamples s) => Isolate.run(() => detect(samplesToImage(s)));
Future<List<int>> _jpegInIsolate(FrameSamples s) =>
    Isolate.run(() => img.encodeJpg(samplesToImage(s), quality: kJpegQuality));

class CaptureResult {
  final Capture capture;
  final bool inGallery;
  const CaptureResult(this.capture, this.inGallery);
}

class CaptureScreen extends StatefulWidget {
  const CaptureScreen({super.key});

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> with WidgetsBindingObserver {
  CameraController? _camera;
  String? _error;
  Size? _screen;

  bool _busy = false; // a frame is being analysed
  bool _saving = false; // gates passed, photo is being saved
  int _frame = 0;
  String? _hint;
  Detection? _last;

  StreamSubscription<AccelerometerEvent>? _accel;
  double _motion = 0;
  int _stillFrames = 0;
  bool _focusLocked = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    if (kUseStillnessAndFocusLock) {
      _accel = accelerometerEventStream(samplingPeriod: SensorInterval.normalInterval).listen(
        (e) {
          final m = math.sqrt(e.x * e.x + e.y * e.y + e.z * e.z);
          _motion = 0.7 * _motion + 0.3 * (m - 9.81).abs();
        },
        onError: (_) => _motion = 0, // no accelerometer: never block capture
        cancelOnError: true,
      );
    }
    _openCamera();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _accel?.cancel();
    _camera?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final c = _camera;
    if (c == null || !c.value.isInitialized) return;
    if (state == AppLifecycleState.inactive) {
      _camera = null;
      c.dispose();
    } else if (state == AppLifecycleState.resumed && !_saving) {
      _openCamera();
    }
  }

  Future<void> _openCamera() async {
    try {
      final cams = await availableCameras();
      final back = cams.firstWhere((c) => c.lensDirection == CameraLensDirection.back, orElse: () => cams.first);
      final c = CameraController(
        back,
        ResolutionPreset.max, // full detail for the bar widths
        enableAudio: false,
        imageFormatGroup: Platform.isIOS ? ImageFormatGroup.bgra8888 : ImageFormatGroup.yuv420,
      );
      await c.initialize();
      await c.setFlashMode(FlashMode.off);
      if (!mounted) return c.dispose();
      setState(() {
        _camera = c;
        _error = null;
      });
      await c.startImageStream(_onFrame);
    } on CameraException catch (e) {
      setState(() => _error = e.code == 'CameraAccessDenied'
          ? 'Camera permission is off. Allow it in Settings to capture.'
          : 'Camera error: ${e.description ?? e.code}');
    } catch (e) {
      setState(() => _error = 'No camera available.');
    }
  }

  Future<void> _onFrame(CameraImage frame) async {
    _frame++;
    if (_busy || _saving || _screen == null || _frame % 3 != 0) return;
    _busy = true;
    try {
      await _analyse(frame);
    } finally {
      _busy = false;
    }
  }

  Future<void> _analyse(CameraImage frame) async {
    final c = _camera!;
    final turns = quarterTurnsFor(frame, c.description.sensorOrientation);
    final (iw, ih) = uprightSize(frame, turns);
    final roi = Roi.inImage(_screen!, Size(iw.toDouble(), ih.toDouble()));
    final step = (iw / kDetectionFrameWidth).round().clamp(1, 8);
    final samples = sampleFrame(frame, turns, roi[0], roi[1], roi[2], roi[3], step: step);
    if (samples == null) return;

    final d = (await _detectInIsolate(samples)).scaled(step);
    _last = d;
    final hint = hintFor(d);
    if (hint != _hint && mounted) setState(() => _hint = hint);
    if (!d.accepted) {
      _stillFrames = 0;
      return;
    }

    if (kUseStillnessAndFocusLock) {
      if (_motion > kStillnessThreshold) {
        _stillFrames = 0;
        return;
      }
      if (++_stillFrames < kStillFramesRequired) return;
      if (!_focusLocked) {
        try {
          await c.setFocusPoint(const Offset(0.5, 0.5));
          await c.setExposurePoint(const Offset(0.5, 0.5));
          await Future.delayed(const Duration(milliseconds: 400));
          await c.setFocusMode(FocusMode.locked);
          await c.setExposureMode(ExposureMode.locked);
        } catch (_) {
          // Some devices refuse the lock; capture anyway.
        }
        _focusLocked = true;
        return; // take the photo from a frame after the lock
      }
    }
    await _save(frame, turns, roi, d);
  }

  Future<void> _save(CameraImage frame, int turns, List<int> roi, Detection d) async {
    setState(() => _saving = true);
    final (iw, ih) = uprightSize(frame, turns);
    final full = sampleFrame(frame, turns, 0, 0, iw, ih)!;
    try {
      await _camera!.stopImageStream();
    } catch (_) {}

    final jpeg = await _jpegInIsolate(full);
    List<int>? toImage(List<int>? p) => p == null ? null : [p[0] + roi[0], p[1] + roi[1]];
    final meta = {
      'app': 'visioncrack_capture 1.0.0',
      'platform': Platform.operatingSystem,
      'image_size': [iw, ih],
      'screen_size_dp': [_screen!.width, _screen!.height],
      'roi_px': {'x': roi[0], 'y': roi[1], 'w': roi[2], 'h': roi[3]},
      ...d.toJson(),
      'corners_image_px': {'tl': toImage(d.tl), 'tr': toImage(d.tr), 'bl': toImage(d.bl), 'br': toImage(d.br)},
      'settings': {
        'roi_alpha': kRoiAlpha,
        'coverage_min': kCoverageMin,
        'rotation_max_deg': kRotationMaxDeg,
        'band_height_px': kBandHeight,
        'stillness_and_focus_lock': kUseStillnessAndFocusLock,
      },
    };
    final (cap, inGallery) = await CaptureStore.save(jpeg, meta);
    if (mounted) Navigator.of(context).pop(CaptureResult(cap, inGallery));
  }

  @override
  Widget build(BuildContext context) {
    final c = _camera;
    return Scaffold(
      backgroundColor: Colors.black,
      body: LayoutBuilder(builder: (context, box) {
        _screen = box.biggest;
        final roi = Roi.onScreen(box.biggest);
        return Stack(children: [
          if (c != null && c.value.isInitialized) Positioned.fill(child: _FullScreenPreview(controller: c)),
          if (_error != null)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white)),
              ),
            )
          else if (c == null)
            const Center(child: CircularProgressIndicator(color: Colors.white)),
          Positioned.fill(child: CustomPaint(painter: _GuidePainter(roi.rect, _last?.accepted ?? false))),
          if (_hint != null && !_saving)
            Positioned(
              top: roi.rect.bottom + 16,
              left: 0,
              right: 0,
              child: Center(child: _Pill(_hint!)),
            ),
          if (_saving)
            Container(
              color: Colors.black54,
              alignment: Alignment.center,
              child: const Column(mainAxisSize: MainAxisSize.min, children: [
                CircularProgressIndicator(color: Colors.white),
                SizedBox(height: 16),
                Text('Saving photo…', style: TextStyle(color: Colors.white)),
              ]),
            ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: IconButton(
                icon: const Icon(Icons.arrow_back, color: Colors.white),
                style: IconButton.styleFrom(backgroundColor: Colors.black45),
                onPressed: _saving ? null : () => Navigator.of(context).pop(),
              ),
            ),
          ),
        ]);
      }),
    );
  }
}

/// Camera preview scaled to fill the screen height (the ROI formula assumes this).
class _FullScreenPreview extends StatelessWidget {
  final CameraController controller;
  const _FullScreenPreview({required this.controller});

  @override
  Widget build(BuildContext context) {
    final p = controller.value.previewSize!;
    final ratio = math.max(p.width, p.height) / math.min(p.width, p.height); // height / width in portrait
    return LayoutBuilder(builder: (context, box) {
      return ClipRect(
        child: OverflowBox(
          maxWidth: double.infinity,
          maxHeight: box.maxHeight,
          child: SizedBox(width: box.maxHeight / ratio, height: box.maxHeight, child: CameraPreview(controller)),
        ),
      );
    });
  }
}

class _GuidePainter extends CustomPainter {
  final Rect roi;
  final bool ok;
  _GuidePainter(this.roi, this.ok);

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawPath(
      Path()
        ..addRect(Offset.zero & size)
        ..addRect(roi)
        ..fillType = PathFillType.evenOdd,
      Paint()..color = Colors.black.withValues(alpha: .35),
    );
    final pen = Paint()
      ..color = ok ? Colors.greenAccent : Colors.redAccent
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 4;
    const l = 20.0;
    final r = roi.inflate(3);
    for (final (p, dx, dy) in [
      (r.topLeft, 1.0, 1.0),
      (r.topRight, -1.0, 1.0),
      (r.bottomLeft, 1.0, -1.0),
      (r.bottomRight, -1.0, -1.0),
    ]) {
      canvas.drawLine(p, p.translate(dx * l, 0), pen);
      canvas.drawLine(p, p.translate(0, dy * l), pen);
    }
  }

  @override
  bool shouldRepaint(_GuidePainter old) => old.roi != roi || old.ok != ok;
}

class _Pill extends StatelessWidget {
  final String text;
  const _Pill(this.text);

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(color: Colors.black.withValues(alpha: .6), borderRadius: BorderRadius.circular(20)),
        child: Text(text, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600)),
      );
}

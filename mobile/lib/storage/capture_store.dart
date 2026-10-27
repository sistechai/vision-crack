// Saved captures: <app documents>/captures/VisionCrack_<unix-ms>.jpg + .json (no GPS).
// Each capture is also copied to the phone gallery (Android: album "VisionCrack"; iOS: Recents).
import 'dart:convert';
import 'dart:io';

import 'package:gal/gal.dart';
import 'package:path_provider/path_provider.dart';

class Capture {
  final File image;
  final DateTime time;
  const Capture(this.image, this.time);

  File get sidecar => File(image.path.replaceFirst(RegExp(r'\.jpg$'), '.json'));
}

class CaptureStore {
  static const album = 'VisionCrack';

  static Future<Directory> _dir() async {
    final d = Directory('${(await getApplicationDocumentsDirectory()).path}/captures');
    if (!await d.exists()) await d.create(recursive: true);
    return d;
  }

  /// Newest first.
  static Future<List<Capture>> list() async {
    final files = (await _dir()).listSync().whereType<File>().where((f) => f.path.endsWith('.jpg'));
    final caps = <Capture>[];
    for (final f in files) {
      final ms = int.tryParse(RegExp(r'_(\d+)\.jpg$').firstMatch(f.path)?.group(1) ?? '');
      caps.add(Capture(f, ms != null ? DateTime.fromMillisecondsSinceEpoch(ms) : f.lastModifiedSync()));
    }
    caps.sort((a, b) => b.time.compareTo(a.time));
    return caps;
  }

  /// Writes the JPEG and its JSON sidecar, then copies the JPEG to the gallery.
  /// Returns the saved capture and whether the gallery copy worked.
  static Future<(Capture, bool)> save(List<int> jpeg, Map<String, dynamic> meta) async {
    final now = DateTime.now();
    final base = '${(await _dir()).path}/VisionCrack_${now.millisecondsSinceEpoch}';
    final image = File('$base.jpg');
    await image.writeAsBytes(jpeg, flush: true);
    await File('$base.json')
        .writeAsString(const JsonEncoder.withIndent('  ').convert({'captured_at': now.toIso8601String(), ...meta}));

    var inGallery = false;
    // iOS: creating an album needs full photo-library (read) access, so the photo goes straight to
    // the library with add-only access. Android: album "VisionCrack" needs no extra permission.
    final useAlbum = Platform.isAndroid;
    try {
      if (await Gal.hasAccess(toAlbum: useAlbum) || await Gal.requestAccess(toAlbum: useAlbum)) {
        await Gal.putImage(image.path, album: useAlbum ? album : null);
        inGallery = true;
      }
    } catch (_) {
      // The app copy is kept even if the gallery refuses.
    }
    return (Capture(image, now), inGallery);
  }
}

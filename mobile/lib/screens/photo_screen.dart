// One capture, full screen, read-only (pinch to zoom).
import 'package:flutter/material.dart';

import '../storage/capture_store.dart';

class PhotoScreen extends StatelessWidget {
  final Capture capture;
  const PhotoScreen({super.key, required this.capture});

  @override
  Widget build(BuildContext context) {
    final t = capture.time;
    String two(int v) => v.toString().padLeft(2, '0');
    final title = '${t.year}-${two(t.month)}-${two(t.day)} ${two(t.hour)}:${two(t.minute)}:${two(t.second)}';
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(title, style: const TextStyle(fontSize: 16)),
      ),
      body: Center(
        child: InteractiveViewer(
          maxScale: 8,
          child: Hero(tag: capture.image.path, child: Image.file(capture.image)),
        ),
      ),
    );
  }
}

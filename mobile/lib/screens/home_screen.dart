// Main screen: saved captures (newest first) and one Capture button.
import 'dart:io';

import 'package:flutter/material.dart';

import '../storage/capture_store.dart';
import 'capture_screen.dart';
import 'photo_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Capture> _captures = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    final caps = await CaptureStore.list();
    if (mounted) {
      setState(() {
        _captures = caps;
        _loading = false;
      });
    }
  }

  Future<void> _capture() async {
    final result = await Navigator.of(context).push<CaptureResult>(
      MaterialPageRoute(builder: (_) => const CaptureScreen()),
    );
    await _reload();
    if (result != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(result.inGallery
            ? (Platform.isAndroid ? 'Saved to the gallery (album "${CaptureStore.album}")' : 'Saved to Photos')
            : 'Saved in the app. Gallery access is off, so it was not copied there.'),
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('VisionCrack')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _captures.isEmpty
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text(
                      'No captures yet.\nPress Capture and fit the VisionCrack label in the box.',
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              : GridView.builder(
                  padding: const EdgeInsets.fromLTRB(4, 4, 4, 96),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3,
                    mainAxisSpacing: 4,
                    crossAxisSpacing: 4,
                    childAspectRatio: 9 / 16,
                  ),
                  itemCount: _captures.length,
                  itemBuilder: (context, i) {
                    final c = _captures[i];
                    return GestureDetector(
                      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PhotoScreen(capture: c))),
                      child: Hero(
                        tag: c.image.path,
                        child: Image.file(c.image, fit: BoxFit.cover, cacheWidth: 360),
                      ),
                    );
                  },
                ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: SizedBox(
        width: 220,
        height: 56,
        child: FloatingActionButton.extended(
          onPressed: _capture,
          icon: const Icon(Icons.camera_alt),
          label: const Text('Capture', style: TextStyle(fontSize: 18)),
        ),
      ),
    );
  }
}

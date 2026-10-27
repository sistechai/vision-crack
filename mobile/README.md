# VisionCrack capture app

The guided-capture part of the paper's app, on its own. It has no login, server, upload or location.

* **Main screen:** your captures, newest first, and one **Capture** button. Tap a photo to view it full screen.
* **Capture screen:** the camera with the guide box. The photo is taken **automatically** once the label is
  found at all four corners, fills the box (> 95 % on each side) and is upright (< 2°). A hint tells you what to fix
  ("Move closer", "Almost there", "Straighten the phone", "Hold steady").
* **Saved:** each photo goes to the gallery album **VisionCrack**, and to the app's own folder together with a
  `.json` file: image size, guide-box position, the four corners, the coverage values and the angle.

## Build and run

Flutter ≥ 3.44 (stable). Print a label first: 50 × 30 mm at 100 % scale (see the main README).

```bash
cd mobile
flutter pub get
flutter test                # detector on data/sample, must match the phone's corners within 2 px
flutter run                 # on a connected phone (the camera does not work in simulators)
```

iOS: open `ios/Runner.xcworkspace` once and choose your own signing team (Runner → Signing & Capabilities).
Android 7.0 (API 24) or newer; iOS 15 or newer.

## Where the paper is in the code

| Paper | File |
|---|---|
| Guide box (ROI), Eq. 1–5: `w = 0.45·W`, `h = 3/5·w`, `x = (W − w)/2`, `y = H − 2h` | `lib/config.dart` → `Roi` |
| HSV red mask (H ≤ 10 or ≥ 160, S ≥ 100, V ≥ 100) | `lib/detection/marker_detector.dart` → `isRed` |
| 2 × 2 red blocks (≥ 3 of 4 pixels red) in the 64-px top and bottom bands | `redBlocks` |
| Corners P1–P4 = red block closest to each corner of the box | `detect` |
| Gate 1 corners, gate 2 coverage > 0.95, gate 3 \|90° − θ\| < 2° | `detect` |
| All constants in one place | `lib/config.dart` |

The same detector in Python is `src/visioncrack/detection.py` and `gates.py`. Notebook 02 shows that it finds the
same corners as the phone.

### Differences from the paper
* **Stillness and focus lock (not in the paper).** After the three gates pass, the app waits until the phone has been
  still for 5 frames, then locks focus and exposure before taking the photo. This only makes the photo sharper and
  doesn't change the geometry. Turn it off with `kUseStillnessAndFocusLock = false` in `lib/config.dart`.
* **Frame orientation.** Android cameras deliver landscape frames. The app turns them upright before applying the
  guide box, so the saved photo is portrait on both platforms, like the paper's 2160 × 3840 captures.

## Not included
Width measurement runs on a computer (`src/visioncrack`, notebooks 04–05), not in the app. The original app's
server upload, projects, maps and dashboard are not part of this release.

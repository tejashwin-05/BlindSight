# EcoSight Flutter Remote Camera Client (v1)

This is a new, isolated Flutter client for the standalone contract server:

- server endpoint: `/v1/analyze-frame`
- service file: `lib/services/remote_camera_contract_v1_client.dart`
- optional stream helper: `lib/services/remote_camera_streamer_v1.dart`

Your existing WebSocket flow remains unchanged.

## Install dependency

```bash
flutter pub get
```

## Basic usage

```dart
import 'dart:typed_data';
import 'package:ecosight_client/services/remote_camera_contract_v1_client.dart';

final api = RemoteCameraContractV1Client(
  baseUrl: 'http://192.168.1.23:8080',
  apiKey: 'supersecret', // optional
);

final ok = await api.healthCheck();
print('health: $ok');

// jpegBytes should be a single JPEG frame from your camera pipeline
Future<void> sendFrame(Uint8List jpegBytes) async {
  final res = await api.analyzeFrame(
    RemoteAnalyzeFrameRequest(
      frameId: DateTime.now().millisecondsSinceEpoch.toString(),
      jpegBytes: jpegBytes,
      include: const RemoteAnalyzeInclude(phase1: true, phase2: false),
    ),
  );

  final nearest = (res.phase1 == null || res.phase1!.isEmpty)
      ? null
      : res.phase1!.first;

  if (nearest != null) {
    print('${nearest.hazard} ${nearest.distance}m ${nearest.direction}');
  }
}
```

## Stream helper (drop-if-busy + throttle)

```dart
import 'dart:typed_data';
import 'package:ecosight_client/services/remote_camera_contract_v1_client.dart';
import 'package:ecosight_client/services/remote_camera_streamer_v1.dart';

final client = RemoteCameraContractV1Client(baseUrl: 'https://your-ngrok-url', apiKey: 'supersecret');
final streamer = RemoteCameraStreamerV1(client: client);

Future<void> onCameraFrame(Uint8List jpegBytes) async {
  final res = await streamer.submitFrame(
    jpegBytes: jpegBytes,
    include: const RemoteAnalyzeInclude(phase1: true, phase2: false),
  );

  if (res == null) {
    // frame skipped due to throttle or in-flight request
    return;
  }

  // use response data
}
```

## Notes for camera plugin integration

- Use any camera package you prefer and convert each frame to JPEG bytes.
- Keep frame size around 480p–720p and JPEG quality ~55–70.
- Recommended send rate: ~4 to 8 FPS.

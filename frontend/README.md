# BlindSight Frontend

React + Vite web application for the BlindSight assistive navigation system.

## Features

### Phase 1 - Real-time Hazard Detection
- Live hazard alerts with direction, distance, and confidence
- Visual urgency indicators (safe, info, warning, critical)
- Text-to-speech announcements for accessibility
- Continuous WebSocket connection to server

### Phase 2 - Scene Description
- On-demand AI-powered scene analysis
- Detailed environment descriptions using Florence-2
- Visual question answering capability

### Additional Features
- Connection status monitoring
- Automatic ping/heartbeat to server
- Responsive design for mobile and desktop
- Local storage for server IP persistence

## Installation

```bash
npm install
```

## Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Build

```bash
npm run build
```

## Usage

1. Start the BlindSight server (see server/README.md)
2. Launch the frontend app
3. Enter the server IP address (e.g., `192.168.1.100:8765`)
4. Click "Connect"
5. View real-time hazard alerts (Phase 1)
6. Click "Describe Scene" for detailed analysis (Phase 2)

## Architecture

```
src/
├── components/
│   ├── HazardAlert.jsx       # Phase 1 hazard display
│   ├── SceneDescription.jsx  # Phase 2 scene analysis
│   ├── ConnectionStatus.jsx  # Connection indicator
│   └── ControlPanel.jsx      # Action buttons
├── hooks/
│   ├── useWebSocket.js       # WebSocket connection management
│   └── useSpeech.js          # Text-to-speech functionality
├── App.jsx                   # Main application
└── main.jsx                  # Entry point
```

## WebSocket Protocol

### Client → Server
```json
{
  "type": "trigger_phase2"
}
```

```json
{
  "type": "ping"
}
```

### Server → Client

Phase 1 (Hazard Alert):
```json
{
  "type": "phase_1",
  "hazard": "person",
  "direction": "left",
  "distance": 2.5,
  "confidence": 0.95,
  "total_hazards": 3
}
```

Phase 2 (Scene Description):
```json
{
  "type": "phase_2",
  "status": "done",
  "description": "A busy street with pedestrians..."
}
```

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Requires WebSocket and Web Speech API support.

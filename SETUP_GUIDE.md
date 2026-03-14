# EcoSight Setup Guide

This guide will help you run the EcoSight project without errors on Windows.

## Project Overview

EcoSight has two main backend components:
1. **Server** - Real-time hazard detection (Python + OpenCV + YOLOv8)
2. **MCP Server** - AI agent tools for navigation, weather, news (Python + MCP)

A web client will connect to these services via WebSocket and HTTP APIs.

## Prerequisites

### Required Software
- Python 3.9+ (3.10 or 3.11 recommended)
- Git
- Visual Studio Build Tools (for Python packages on Windows)
- Node.js 18+ (for web client development)

### Optional
- CUDA Toolkit (for GPU acceleration with PyTorch)

## Step 1: Server Setup

### 1.1 Install Python Dependencies

```cmd
cd server
pip install -r requirements.txt
```

**Common Issues:**
- If `torch` installation fails, install manually:
  ```cmd
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
  ```
- If `opencv-python` fails, try:
  ```cmd
  pip install opencv-python-headless==4.9.0.80
  ```

### 1.2 Download YOLOv8 Model

The server needs `yolov8n.pt` in the `server/` directory. If missing:

```cmd
cd server
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### 1.3 Configure Environment Variables (Optional)

For Twilio SMS alerts (guardian feature):

```cmd
set TWILIO_ACCOUNT_SID=your_account_sid
set TWILIO_AUTH_TOKEN=your_auth_token
set TWILIO_FROM_NUMBER=your_twilio_number
set GUARDIAN_PHONE_NUMBER=+1234567890
```

### 1.4 Test Server

```cmd
cd server
python main.py
```

**Expected Output:**
```
=======================================================
  EcoSight Server — Starting Up
=======================================================
[WS] Server listening on ws://0.0.0.0:8765
[WS] Connect app to: 192.168.x.x : 8765
```

**Troubleshooting:**
- **Camera Error**: If camera fails, run in server-only mode:
  ```cmd
  set ECOSIGHT_SERVER_ONLY=1
  python main.py
  ```
- **Port in use**: Change port in `server/config.py` (WEBSOCKET_PORT)

## Step 2: MCP Server Setup

### 2.1 Install Dependencies

```cmd
cd mcp_server
pip install -r requirements.txt
```

### 2.2 Configure API Keys

Create `.env` file in `mcp_server/` directory:

```env
ORS_API_KEY=your_openrouteservice_key
OWM_API_KEY=your_openweathermap_key
NEWS_API_KEY=your_newsapi_key
```

**Get Free API Keys:**
- OpenRouteService: https://openrouteservice.org/dev/#/signup
- OpenWeatherMap: https://openweathermap.org/api
- NewsAPI: https://newsapi.org

**Note:** The `.env.example` file contains demo keys, but they may have rate limits.

### 2.3 Test MCP Server

```cmd
cd mcp_server
python -m mcp_server
```

**Expected Output:**
```
INFO:ecosight-mcp:Starting EcoSight MCP Server (stdio)
```

Press Ctrl+C to stop.

## Step 3: Frontend Setup

### 3.1 Install Node.js Dependencies

```cmd
cd frontend
npm install
```

### 3.2 Start Development Server

```cmd
npm run dev
```

Or use the batch file:
```cmd
start_frontend.bat
```

**Expected Output:**
```
VITE ready in XXX ms
➜  Local:   http://localhost:3000/
```

### 3.3 Connect to Server

1. Open browser to `http://localhost:3000`
2. Enter server IP (e.g., `192.168.1.100:8765` or `localhost:8765`)
3. Click "Connect"
4. View real-time hazard alerts
5. Click "Describe Scene" for Phase 2 analysis

## Step 4: Running the Complete System

### Option A: Manual Start (Recommended)

**Terminal 1 - Main Server:**
```cmd
start_server.bat
```
Or manually:
```cmd
cd server
python main.py
```

**Terminal 2 - Frontend:**
```cmd
start_frontend.bat
```
Or manually:
```cmd
cd frontend
npm run dev
```

**Terminal 3 - MCP Server (optional, for AI agent tools):**
```cmd
start_mcp_server.bat
```
Or manually:
```cmd
cd mcp_server
python -m mcp_server --sse --port 8100
```

The frontend will connect to:
- WebSocket: `ws://localhost:8765` (hazard detection stream)
- MCP Server: `http://localhost:8100` (AI tools via SSE - optional)

### Option B: Server-Only Mode (No Camera)

If you don't have a camera or want to test the WebSocket server only:

```cmd
cd server
set ECOSIGHT_SERVER_ONLY=1
set ECOSIGHT_HEADLESS=1
python main.py
```

## Common Issues & Solutions

### Issue: "No module named 'cv2'"
**Solution:**
```cmd
pip install opencv-python==4.9.0.80
```

### Issue: "CUDA not available" or slow inference
**Solution:** This is normal on CPU. For GPU:
1. Install CUDA Toolkit 11.8
2. Reinstall PyTorch with CUDA:
   ```cmd
   pip uninstall torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

### Issue: "Port 8765 already in use"
**Solution:** Kill the process or change port in `server/config.py`

### Issue: "transformers model not found"
**Solution:** Models will download automatically on first run. Ensure internet connection.

### Issue: WebSocket connection fails from web client
**Solution:**
1. Check server is running and shows IP address
2. Update WebSocket URL in web client to match server IP
3. Ensure firewall allows port 8765
4. For remote connections, use server's network IP instead of localhost

## Testing Without Hardware

### Test Server Without Camera
```cmd
cd server
set ECOSIGHT_SERVER_ONLY=1
python main.py
```

### Test MCP Server Tools
```cmd
cd mcp_server
python -c "from tools.accessibility import get_current_time_and_date; import asyncio; print(asyncio.run(get_current_time_and_date()))"
```

## Next Steps

1. **Build web client** to connect to WebSocket (port 8765) and MCP Server (port 8100)
2. **Test Phase 1** (hazard detection) by pointing camera at objects
3. **Test Phase 2** (scene description) by triggering from web interface
4. **Test MCP tools** by integrating with Claude or other MCP clients

## Architecture Summary

```
┌─────────────────┐
│  React Frontend │ ←→ WebSocket (port 8765) ←→ ┌──────────────┐
│  (Vite + React) │                              │ Main Server  │
│  localhost:3000 │ ←→ HTTP/SSE (port 8100)  ←→ │ (Phase 1+2)  │
└─────────────────┘                              └──────────────┘
        ↓                                               ↓
   [Browser APIs]                               ┌──────────────┐
   - WebSocket                                  │  MCP Server  │
   - Speech Synthesis                           │ (AI Tools)   │
   - Geolocation                                └──────────────┘
```

## Frontend Features

### Phase 1 - Real-time Hazard Detection
- Live hazard alerts with direction, distance, confidence
- Visual urgency indicators (safe, info, warning, critical)
- Text-to-speech announcements
- Continuous WebSocket connection

### Phase 2 - Scene Description
- On-demand AI scene analysis
- Florence-2 powered descriptions
- TTS for accessibility

### UI Components
- Connection status monitoring
- Automatic ping/heartbeat
- Responsive mobile-first design
- Server IP persistence

## Performance Tips

1. **Lower YOLO resolution** in `server/config.py`: `PHASE1_IMGSZ = 320`
2. **Reduce FPS** in `server/config.py`: `PHASE1_TARGET_FPS = 5`
3. **Use CPU-only mode** if GPU causes issues
4. **Disable Phase 2 preload**: `PHASE2_PRELOAD_ON_START = False` (already default)
5. **Frontend optimization**: Build for production with `npm run build`

## Quick Start (All-in-One)

1. **Start Server:**
   ```cmd
   start_server.bat
   ```

2. **Start Frontend:**
   ```cmd
   start_frontend.bat
   ```

3. **Open Browser:**
   - Navigate to `http://localhost:3000`
   - Enter server IP: `localhost:8765`
   - Click "Connect"

4. **Test Features:**
   - View real-time hazard detection
   - Click "Describe Scene" for AI analysis
   - Check browser console for WebSocket messages

## Support

Check the individual README files:
- `server/` - Main server documentation
- `mcp_server/README.md` - MCP server tools and API setup
- `frontend/README.md` - React frontend documentation

## Project Structure

```
EcoSight/
├── server/              # Python backend (Phase 1 + 2)
│   ├── main.py         # WebSocket server
│   ├── phase1_reflex.py
│   ├── phase2_context.py
│   └── config.py
├── mcp_server/         # MCP tools (optional)
│   ├── tools/
│   └── server.py
├── frontend/           # React + Vite web app
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── App.jsx
│   └── package.json
├── start_server.bat    # Launch main server
├── start_frontend.bat  # Launch React app
└── SETUP_GUIDE.md     # This file
```

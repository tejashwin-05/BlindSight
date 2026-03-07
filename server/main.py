"""
EcoSight — Main Server
WebSocket server that streams Phase 1 hazard data in real time
and handles Phase 2 on-demand scene description requests.

Architecture:
    camera.py      → Frame capture + skip logic
    phase1_reflex  → YOLOv8 detection + depth + direction
    debounce.py    → Anti-spam cooldown per hazard
    schema.py      → JSON message builders
    phase2_context → Florence-2 captioning (on-demand)
    config.py      → All tuneable constants
"""

import asyncio
import json
import time
import threading
import platform
import os
import cv2
import numpy as np
import websockets
import pyttsx3

import config
from camera import CameraManager
from phase1_reflex import ReflexLayer
from phase2_context import ContextLayer
from debounce import HazardDebouncer
from schema import build_phase1_payload, build_phase2_payload, build_pong
from connection_watchdog import ConnectionWatchdog

HEADLESS_MODE = os.getenv("ECOSIGHT_HEADLESS", "0") == "1"
SERVER_ONLY_MODE = os.getenv("ECOSIGHT_SERVER_ONLY", "0") == "1"


# ─── Shared State ────────────────────────────────────────────────
class ServerState:
    """Mutable shared state across the event loop."""
    def __init__(self):
        self.clients: set = set()
        self.current_frame: np.ndarray | None = None
        self.phase2_requested = False
        self.running = True


state = ServerState()
camera = CameraManager() if not SERVER_ONLY_MODE else None
reflex = ReflexLayer() if not SERVER_ONLY_MODE else None
context = None
debouncer = HazardDebouncer() if not SERVER_ONLY_MODE else None
watchdog = ConnectionWatchdog()

# ─── Server-Side TTS (runs on laptop speakers) ──────────────────
import queue

_tts_queue: queue.Queue = queue.Queue()


def _speak_pyttsx3(text: str) -> bool:
    """Speak text using pyttsx3."""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 170)
        engine.setProperty('volume', 1.0)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        return True
    except Exception as e:
        print(f"[TTS] pyttsx3 error: {e}")
        return False


def _beep_fallback() -> bool:
    """Last-resort audible alert if speech backends fail."""
    try:
        if platform.system().lower().startswith("win"):
            import winsound
            winsound.Beep(1200, 220)
            winsound.Beep(1000, 220)
            return True
        return False
    except Exception as e:
        print(f"[TTS] Beep fallback error: {e}")
        return False

def _tts_worker():
    """Single dedicated TTS thread with stable speech + beep fallback."""
    print("[TTS] Worker ready (backend=pyttsx3)")
    while True:
        text = _tts_queue.get()  # blocks until something is queued
        if text is None:
            break
        try:
            # Drain any newer messages — only speak the latest relevant alert
            while not _tts_queue.empty():
                text = _tts_queue.get_nowait()
            print(f"[TTS-SPEAK] {text}")

            spoke = _speak_pyttsx3(text)
            if not spoke:
                spoke = _beep_fallback()
                if spoke:
                    print("[TTS] Speech unavailable, played beep fallback")

            if not spoke:
                print("[TTS] All speech backends failed for this alert")
        except Exception as e:
            print(f"[TTS] Error: {e}")

# Start the TTS worker thread once
_tts_thread = threading.Thread(target=_tts_worker, daemon=True)
_tts_thread.start()

def speak_alert(text: str):
    """Queue text for the TTS worker thread."""
    _tts_queue.put(text)


def _box_center(box: list[int]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _box_iou(box_a: list[int], box_b: list[int]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union


def _match_target_detection(detections: list[dict], tracked: dict) -> dict | None:
    """
    Find the best matching detection for the currently tracked target.
    Match by hazard class + closest box center.
    """
    if not tracked:
        return None

    tracked_center = _box_center(tracked["box"])
    candidates = [d for d in detections if d["hazard"] == tracked["hazard"]]
    if not candidates:
        return None

    best = min(
        candidates,
        key=lambda d: abs(_box_center(d["box"])[0] - tracked_center[0]) + abs(_box_center(d["box"])[1] - tracked_center[1]),
    )
    best_center = _box_center(best["box"])
    center_delta = abs(best_center[0] - tracked_center[0]) + abs(best_center[1] - tracked_center[1])

    if center_delta > config.TARGET_MATCH_CENTER_TOLERANCE_PX:
        return None
    return best


def _pick_next_target(detections: list[dict], exclude_box: list[int] | None = None) -> dict | None:
    """Pick nearest detection, optionally excluding a specific box."""
    if not detections:
        return None

    if exclude_box is None:
        return detections[0]

    ex_cx, ex_cy = _box_center(exclude_box)
    for det in detections:
        cx, cy = _box_center(det["box"])
        if abs(cx - ex_cx) + abs(cy - ex_cy) > config.TARGET_MATCH_CENTER_TOLERANCE_PX:
            return det
    return None


def _is_in_forward_path_zone(box: list[int], frame_shape: tuple[int, int, int]) -> bool:
    """Return True if a detection is inside the forward walking/driving path."""
    frame_h, frame_w = frame_shape[0], frame_shape[1]
    x1, y1, x2, y2 = box
    center_x = (x1 + x2) / 2.0
    center_ratio = center_x / max(frame_w, 1)
    bottom_ratio = y2 / max(frame_h, 1)

    in_lane = config.PATH_ZONE_X_START <= center_ratio <= config.PATH_ZONE_X_END
    near_ground = bottom_ratio >= config.PATH_ZONE_MIN_BOTTOM_Y_RATIO
    return in_lane and near_ground


def _preprocess_path_detections(detections: list[dict], frame_shape: tuple[int, int, int]) -> list[dict]:
    """
    Preprocess detections for stable single-target tracking:
      1) keep only forward-path boxes
      2) keep only valid distance range
      3) sort nearest first
      4) merge duplicates/overlapping boxes
    """
    filtered = [
        d for d in detections
        if _is_in_forward_path_zone(d["box"], frame_shape)
        and config.DETECTION_MIN_DISTANCE_M <= d["distance"] <= config.DETECTION_MAX_DISTANCE_M
    ]
    filtered.sort(key=lambda d: d["distance"])

    merged: list[dict] = []
    for det in filtered:
        det_center = _box_center(det["box"])
        is_duplicate = False
        for kept in merged:
            kept_center = _box_center(kept["box"])
            center_delta = abs(det_center[0] - kept_center[0]) + abs(det_center[1] - kept_center[1])
            overlap = _box_iou(det["box"], kept["box"])
            if (
                overlap >= config.DETECTION_MERGE_IOU_THRESHOLD
                or center_delta <= config.DETECTION_MERGE_CENTER_DISTANCE_PX
            ):
                is_duplicate = True
                break
        if not is_duplicate:
            merged.append(det)

    return merged


# ─── WebSocket Handler ───────────────────────────────────────────
async def ws_handler(websocket):
    """Handle a new client connection."""
    state.clients.add(websocket)
    client_addr = websocket.remote_address
    print(f"[WS] Client connected: {client_addr}")

    # Register with the connection watchdog (resets failure counters on reconnect)
    watchdog.register(websocket)

    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "trigger_phase2":
                print("[WS] Phase 2 trigger received from client")
                state.phase2_requested = True

            elif msg_type == "ping":
                # Update watchdog heartbeat (with optional GPS)
                watchdog.heartbeat(
                    websocket,
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                )
                await websocket.send(json.dumps(build_pong()))

            elif msg_type == "location_update":
                # Dedicated location message from client
                watchdog.heartbeat(
                    websocket,
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                )

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        state.clients.discard(websocket)
        print(f"[WS] Client disconnected: {client_addr}")
        # Notify watchdog — starts the reconnect-failure countdown
        watchdog.on_disconnect(websocket)


async def broadcast(payload: dict):
    """Send a JSON payload to all connected clients."""
    if not state.clients:
        return
    message = json.dumps(payload)
    await asyncio.gather(
        *(client.send(message) for client in state.clients),
        return_exceptions=True,
    )


# ─── Phase 1 Loop ────────────────────────────────────────────────
async def phase1_loop():
    """Continuously capture frames, run detection, and broadcast."""
    global camera, reflex, debouncer

    if camera is None:
        camera = CameraManager()
    if reflex is None:
        reflex = ReflexLayer()
    if debouncer is None:
        debouncer = HazardDebouncer()

    target_interval = 1.0 / config.PHASE1_TARGET_FPS
    frames_processed = 0
    start_time = time.perf_counter()
    
    # Phase 1 loop state
    last_detections = []
    tracked_target: dict | None = None
    tracked_lost_frames = 0
    switch_candidate: dict | None = None
    switch_candidate_frames = 0
    
    # Initialize Judge View (disabled in headless mode)
    if not HEADLESS_MODE:
        cv2.namedWindow("Judge View", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Judge View", 800, 600)

    try:
        while state.running:
            loop_start = time.perf_counter()

            # ── Read frame (with skip logic inside CameraManager) ─
            should_process, frame = camera.read()

            if frame is None:
                await asyncio.sleep(0.01)
                continue

            state.current_frame = frame
            
            # ── Handle Phase 2 request (interrupts Phase 1 briefly) ─
            if state.phase2_requested:
                state.phase2_requested = False
                debouncer.reset()          # clear cooldowns on mode switch
                # Draw "Scanning..." overlay before switching
                if not HEADLESS_MODE:
                    cv2.putText(frame, "PHASE 2: SCANNING SCENE...", (50, 240), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
                    cv2.imshow("Judge View", frame)
                    cv2.waitKey(1)
                
                await handle_phase2(frame)
                continue

            # ── Run Phase 1 detection (only on target frames) ────────
            if should_process:
                try:
                    detections = reflex.process_frame(frame)
                except Exception as e:
                    print(f"[Phase1] Detector error: {e}")
                    await broadcast(build_phase1_payload(None, None, None, None, 0))
                    await asyncio.sleep(0.02)
                    continue

                last_detections = detections # Update visualization cache
                frames_processed += 1

                if detections:
                    # Preprocess first so single-target tracking sees clean nearest objects.
                    path_detections = _preprocess_path_detections(detections, frame.shape)

                    if not path_detections:
                        tracked_target = None
                        tracked_lost_frames = 0
                        switch_candidate = None
                        switch_candidate_frames = 0
                        await broadcast(build_phase1_payload(None, None, None, None, 0))
                        continue

                    # Target lock: keep current target until passed/lost,
                    # otherwise start with nearest obstacle.
                    if tracked_target is None:
                        selected = path_detections[0]
                        tracked_target = {
                            **selected,
                            "was_near": selected["distance"] <= config.NEAR_HAZARD_DISTANCE_M,
                        }
                        tracked_lost_frames = 0
                    else:
                        matched = _match_target_detection(path_detections, tracked_target)
                        if matched is not None:
                            tracked_lost_frames = 0
                            previous_distance = tracked_target["distance"]
                            was_near = tracked_target.get("was_near", False)
                            is_near = matched["distance"] <= config.NEAR_HAZARD_DISTANCE_M
                            was_near = was_near or is_near

                            passed_current = (
                                was_near
                                and (matched["distance"] - previous_distance) >= config.PASS_DISTANCE_INCREASE_M
                                and matched["distance"] > config.NEAR_HAZARD_DISTANCE_M
                            )

                            if passed_current:
                                next_target = _pick_next_target(path_detections, exclude_box=matched["box"])
                                if next_target is not None:
                                    if switch_candidate is None:
                                        switch_candidate = next_target
                                        switch_candidate_frames = 1
                                    else:
                                        same_candidate = (
                                            switch_candidate["hazard"] == next_target["hazard"]
                                            and abs(_box_center(switch_candidate["box"])[0] - _box_center(next_target["box"])[0])
                                            + abs(_box_center(switch_candidate["box"])[1] - _box_center(next_target["box"])[1])
                                            <= config.TARGET_MATCH_CENTER_TOLERANCE_PX
                                        )
                                        if same_candidate:
                                            switch_candidate_frames += 1
                                        else:
                                            switch_candidate = next_target
                                            switch_candidate_frames = 1

                                    if switch_candidate_frames >= config.PHASE1_LOCK_SWITCH_CONFIRM_FRAMES:
                                        tracked_target = {
                                            **next_target,
                                            "was_near": next_target["distance"] <= config.NEAR_HAZARD_DISTANCE_M,
                                        }
                                        switch_candidate = None
                                        switch_candidate_frames = 0
                                else:
                                    tracked_target = None
                                    switch_candidate = None
                                    switch_candidate_frames = 0
                            else:
                                tracked_target = {
                                    **matched,
                                    "was_near": was_near,
                                }
                                switch_candidate = None
                                switch_candidate_frames = 0
                        else:
                            tracked_lost_frames += 1
                            if tracked_lost_frames >= config.TARGET_LOST_FRAMES_TO_SWITCH:
                                selected = path_detections[0]
                                tracked_target = {
                                    **selected,
                                    "was_near": selected["distance"] <= config.NEAR_HAZARD_DISTANCE_M,
                                }
                                tracked_lost_frames = 0
                                switch_candidate = None
                                switch_candidate_frames = 0

                    active_target = tracked_target if tracked_target is not None else path_detections[0]

                    payload = None
                    if debouncer.should_alert(active_target["hazard"], active_target["distance"]):
                        payload = build_phase1_payload(
                            hazard=active_target["hazard"],
                            direction=active_target["direction"],
                            distance=active_target["distance"],
                            confidence=active_target["confidence"],
                            total_hazards=len(path_detections),
                        )
                    
                    # If we found an alert, broadcast it
                    if payload:
                        guidance_text = active_target.get("guidance", "")
                        if payload["distance"] is not None and payload["distance"] <= config.NEAR_HAZARD_DISTANCE_M:
                            msg = (
                                f"Hazard near: {payload['hazard']} on your {payload['direction']}, "
                                f"{payload['distance']} meters"
                            )
                        else:
                            msg = (
                                f"Next object: {payload['hazard']} on your {payload['direction']}, "
                                f"{payload['distance']} meters"
                            )
                        if guidance_text:
                            msg = f"{msg}. {guidance_text}."
                        print(f"[TTS-QUEUE] {msg}")
                        speak_alert(msg)
                        await broadcast(payload)
                    else:
                        # Heartbeat if all hazards strictly debounced
                        await broadcast(build_phase1_payload(None, None, None, None, len(path_detections)))
                else:
                    tracked_target = None
                    tracked_lost_frames = 0
                    switch_candidate = None
                    switch_candidate_frames = 0
                    # No hazards
                    await broadcast(build_phase1_payload(None, None, None, None, 0))

            if not HEADLESS_MODE:
                # ── DRAW JUDGE VIEW (On Every Frame) ─────────────────
                vis_frame = frame.copy()
                for det in last_detections:
                    x1, y1, x2, y2 = det.get("box", [0, 0, 0, 0])
                    label = f"{det['hazard']} {det['distance']}m"
                    color = (0, 0, 255) # Red for danger

                    cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
                    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                    cv2.rectangle(vis_frame, (x1, y1 - 20), (x1 + w, y1), color, -1)
                    cv2.putText(vis_frame, label, (x1, y1 - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

                status_text = f"Phase 1: Active | Hazards: {len(last_detections)}"
                cv2.putText(vis_frame, status_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.imshow("Judge View", vis_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    state.running = False
                    break

            # ── FPS counter (every 30 processed frames) ──────────────
            if frames_processed > 0 and frames_processed % 30 == 0:
                elapsed = time.perf_counter() - start_time
                fps = frames_processed / elapsed if elapsed > 0 else 0
                print(f"[Phase1] Processing at {fps:.1f} FPS")

            # ── Frame‑rate throttle ──────────────────────────────────
            # Only sleep if we processed a frame and need to maintain target FPS
            # If we skipped, we loop immediately to drain the camera buffer
            if should_process:
                elapsed = time.perf_counter() - loop_start
                sleep_time = target_interval - elapsed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")
    finally:
        # These cleanups are better handled in main() finally, 
        # but since we opened the window here, we can close it here or in main.
        # Ideally loop just returns and main handles cleanup.
        pass


# ─── Phase 2 Handler ─────────────────────────────────────────────
async def handle_phase2(frame: np.ndarray):
    """Run Florence-2 scene description on the current frame."""
    global context

    if context is None:
        context = ContextLayer()

    print("[Phase2] Processing scene description...")

    await broadcast(build_phase2_payload(status="processing"))

    # Run heavy model in a thread to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    try:
        description = await loop.run_in_executor(
            None, context.describe_scene, frame
        )
    except Exception as e:
        err = f"Phase 2 unavailable: {e}"
        print(f"[Phase2] Error: {e}")
        await broadcast(build_phase2_payload(status="done", description=err))
        return

    print(f"[Phase2] Description: {description[:80]}...")
    await broadcast(build_phase2_payload(status="done", description=description))


# ─── Main Entry ──────────────────────────────────────────────────
async def main():
    print("=" * 55)
    print("  EcoSight Server — Starting Up")
    print("=" * 55)

    if SERVER_ONLY_MODE:
        print("[Server] Running in server-only mode (no camera, no OpenCV output)")
    else:
        global camera
        if camera is None:
            camera = CameraManager()
        camera.open()

    # Optional Phase-2 preload (disabled by default to protect Phase-1 latency)
    if config.PHASE2_PRELOAD_ON_START:
        global context
        if context is None:
            context = ContextLayer()
        loop = asyncio.get_event_loop()
        preload_future = asyncio.ensure_future(
            loop.run_in_executor(None, context.load_model)
        )

        def _on_phase2_preload_done(fut: asyncio.Future):
            exc = fut.exception()
            if exc is not None:
                print(f"[Phase2] Preload failed: {exc}")

        preload_future.add_done_callback(_on_phase2_preload_done)

    # Start WebSocket server
    server = await websockets.serve(
        ws_handler,
        config.WEBSOCKET_HOST,
        config.WEBSOCKET_PORT,
    )
    
    # Print local IP for easy connection
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"[WS] Server listening on ws://{config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT}")
    print(f"[WS] Connect app to: {local_ip} : {config.WEBSOCKET_PORT}")

    try:
        if SERVER_ONLY_MODE:
            while state.running:
                await asyncio.sleep(0.2)
        else:
            await phase1_loop()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")
    finally:
        if not SERVER_ONLY_MODE:
            camera.release()
        if not HEADLESS_MODE:
            cv2.destroyAllWindows()
        server.close()
        await server.wait_closed()
        print("[Server] Stopped.")


if __name__ == "__main__":
    asyncio.run(main())

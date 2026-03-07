"""
EcoSight Remote Camera Contract Server (v1)
Standalone, opt-in server for phone -> laptop frame processing.

This file is intentionally isolated from the existing WebSocket runtime
so failures here do not affect the current working pipeline.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np

# ── Import guardian alert (lives one directory up) ───────────────
import sys
_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from guardian_alert import send_guardian_alert
import config as ecosight_config


@dataclass
class ServerConfig:
    host: str = os.getenv("ECOSIGHT_REMOTE_HOST", "0.0.0.0")
    port: int = int(os.getenv("ECOSIGHT_REMOTE_PORT", "8080"))
    api_key: str = os.getenv("ECOSIGHT_REMOTE_API_KEY", "")
    max_jpeg_bytes: int = int(os.getenv("ECOSIGHT_REMOTE_MAX_JPEG_BYTES", str(2 * 1024 * 1024)))


CONFIG = ServerConfig()

_reflex = None
_context = None
_latest_lock = threading.Lock()
_latest_frame_jpeg: bytes | None = None
_latest_frame_ts_ms: int | None = None
_latest_frame_id: str | None = None

# ─── Connection Watchdog (HTTP polling approach) ──────────────────
# For the HTTP-based remote camera contract the "heartbeat" is the
# latest frame submission or an explicit /v1/heartbeat POST.
# A background thread checks if any client has gone silent.

@dataclass
class _ClientHeartbeat:
    ip: str
    last_seen: float = field(default_factory=time.time)
    latitude: float | None = None
    longitude: float | None = None
    missed_windows: int = 0
    alert_sent: bool = False

_heartbeat_lock = threading.Lock()
_heartbeats: dict[str, _ClientHeartbeat] = {}      # keyed by client IP
_watchdog_thread: threading.Thread | None = None
_watchdog_running = False


def _watchdog_touch(ip: str, lat: float | None = None, lng: float | None = None):
    """Record that we heard from a client (frame upload or heartbeat)."""
    with _heartbeat_lock:
        rec = _heartbeats.get(ip)
        if rec is None:
            rec = _ClientHeartbeat(ip=ip)
            _heartbeats[ip] = rec
        rec.last_seen = time.time()
        rec.missed_windows = 0  # reset on every touch
        rec.alert_sent = False  # allow re-alert if they reconnect then drop again
        if lat is not None:
            rec.latitude = lat
        if lng is not None:
            rec.longitude = lng


def _watchdog_loop():
    """Background thread: check every WINDOW seconds if any client went silent."""
    window = getattr(ecosight_config, 'WATCHDOG_RECONNECT_WINDOW_SEC', 15)
    max_misses = getattr(ecosight_config, 'WATCHDOG_MAX_RECONNECT_ATTEMPTS', 3)
    print(f"[Watchdog] Started — window={window}s, max_misses={max_misses}")

    while _watchdog_running:
        time.sleep(window)
        now = time.time()
        with _heartbeat_lock:
            for ip, rec in list(_heartbeats.items()):
                silent_sec = now - rec.last_seen
                if silent_sec >= window:
                    rec.missed_windows += 1
                    print(
                        f"[Watchdog] Client {ip} silent for {silent_sec:.0f}s "
                        f"— miss {rec.missed_windows}/{max_misses}"
                    )
                    if rec.missed_windows >= max_misses and not rec.alert_sent:
                        rec.alert_sent = True
                        print(f"[Watchdog] ⚠️  Sending guardian alert for {ip}!")
                        # Run SMS in a separate thread so we don't block the watchdog
                        threading.Thread(
                            target=send_guardian_alert,
                            kwargs={
                                'latitude': rec.latitude,
                                'longitude': rec.longitude,
                            },
                            daemon=True,
                        ).start()


def _start_watchdog():
    global _watchdog_thread, _watchdog_running
    if _watchdog_thread is not None:
        return
    _watchdog_running = True
    _watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
    _watchdog_thread.start()


def get_reflex_layer():
    global _reflex
    if _reflex is None:
        from phase1_reflex import ReflexLayer

        _reflex = ReflexLayer()
    return _reflex


def get_context_layer():
    global _context
    if _context is None:
        from phase2_context import ContextLayer

        _context = ContextLayer()
    return _context


def _decode_jpeg_from_base64(frame_b64: str, max_bytes: int) -> np.ndarray:
    try:
        raw = base64.b64decode(frame_b64, validate=True)
    except Exception as exc:
        raise ValueError(f"Invalid base64 payload: {exc}") from exc

    if len(raw) == 0:
        raise ValueError("Empty image payload")
    if len(raw) > max_bytes:
        raise ValueError(f"Image too large: {len(raw)} bytes (max={max_bytes})")

    buf = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Invalid JPEG bytes")
    return frame


def _decode_jpeg_and_raw_from_base64(frame_b64: str, max_bytes: int) -> tuple[np.ndarray, bytes]:
    try:
        raw = base64.b64decode(frame_b64, validate=True)
    except Exception as exc:
        raise ValueError(f"Invalid base64 payload: {exc}") from exc

    if len(raw) == 0:
        raise ValueError("Empty image payload")
    if len(raw) > max_bytes:
        raise ValueError(f"Image too large: {len(raw)} bytes (max={max_bytes})")

    buf = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Invalid JPEG bytes")
    return frame, raw


def _normalize_phase2_mode(mode: str) -> str:
    mode = (mode or "").strip().lower()
    if mode in ("caption", "describe", "scene"):
        return "caption"
    if mode in ("ocr", "text"):
        return "ocr"
    if mode in ("vqa", "question", "qa"):
        return "vqa"
    raise ValueError("phase2.mode must be one of: caption | ocr | vqa")


class RemoteCameraHandler(BaseHTTPRequestHandler):
    server_version = "EcoSightRemoteContractV1/1.0"

    def _write_json(self, code: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _unauthorized(self):
        self._write_json(
            HTTPStatus.UNAUTHORIZED,
            {
                "ok": False,
                "error": "unauthorized",
                "message": "Missing or invalid X-API-Key",
            },
        )

    def _write_bytes(self, code: int, content_type: str, payload: bytes):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _check_api_key(self) -> bool:
        if not CONFIG.api_key:
            return True
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        query_key = (query.get("api_key", [""])[0] or "").strip()
        header_key = self.headers.get("X-API-Key", "")
        return header_key == CONFIG.api_key or query_key == CONFIG.api_key

    def do_GET(self):
        parsed = urlparse(self.path)
        path_only = parsed.path

        if path_only == "/health":
            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "service": "ecosight-remote-camera-contract-v1",
                    "guardian_alert_enabled": bool(
                        getattr(ecosight_config, 'GUARDIAN_PHONE_NUMBER', '')
                    ),
                    "ts": int(time.time() * 1000),
                },
            )
            return

        # ── Watchdog status (GET) ────────────────────────────────
        if path_only == "/v1/watchdog-status":
            now = time.time()
            with _heartbeat_lock:
                clients = [
                    {
                        "ip": rec.ip,
                        "seconds_ago": round(now - rec.last_seen, 1),
                        "latitude": rec.latitude,
                        "longitude": rec.longitude,
                        "missed_windows": rec.missed_windows,
                        "alert_sent": rec.alert_sent,
                    }
                    for rec in _heartbeats.values()
                ]
            self._write_json(
                HTTPStatus.OK,
                {"ok": True, "clients": clients, "ts": int(now * 1000)},
            )
            return

        if path_only == "/v1/latest-frame.jpg":
            if not self._check_api_key():
                self._unauthorized()
                return
            with _latest_lock:
                latest = _latest_frame_jpeg
            if latest is None:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {
                        "ok": False,
                        "error": "no_frame",
                        "message": "No frame received yet",
                    },
                )
                return
            self._write_bytes(HTTPStatus.OK, "image/jpeg", latest)
            return

        if path_only == "/v1/latest-frame-meta":
            if not self._check_api_key():
                self._unauthorized()
                return
            with _latest_lock:
                ts = _latest_frame_ts_ms
                frame_id = _latest_frame_id
                has_frame = _latest_frame_jpeg is not None
            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "has_frame": has_frame,
                    "frame_id": frame_id,
                    "ts": ts,
                },
            )
            return

        if path_only == "/v1/stream.mjpg":
            if not self._check_api_key():
                self._unauthorized()
                return

            boundary = "frame"
            self.send_response(HTTPStatus.OK)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Pragma", "no-cache")
            self.send_header("Connection", "close")
            self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={boundary}")
            self.end_headers()

            try:
                last_sent_ts = None
                while True:
                    with _latest_lock:
                        frame = _latest_frame_jpeg
                        frame_ts = _latest_frame_ts_ms

                    if frame is None:
                        time.sleep(0.08)
                        continue

                    if last_sent_ts is not None and frame_ts == last_sent_ts:
                        time.sleep(0.03)
                        continue

                    self.wfile.write(f"--{boundary}\r\n".encode("ascii"))
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()

                    last_sent_ts = frame_ts
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                pass
            return

        self._write_json(
            HTTPStatus.NOT_FOUND,
            {
                "ok": False,
                "error": "not_found",
                "message": "Use GET /health, GET /v1/latest-frame.jpg, GET /v1/latest-frame-meta, GET /v1/stream.mjpg or POST /v1/analyze-frame",
            },
        )

    def do_POST(self):
        parsed = urlparse(self.path)
        path_only = parsed.path

        # ── Heartbeat endpoint (lightweight, with GPS) ────────────
        if path_only == "/v1/heartbeat":
            if not self._check_api_key():
                self._unauthorized()
                return
            try:
                content_len = int(self.headers.get("Content-Length", "0"))
                body = {}
                if content_len > 0:
                    raw = self.rfile.read(content_len)
                    body = json.loads(raw.decode("utf-8"))
            except Exception:
                body = {}

            client_ip = self.client_address[0]
            _watchdog_touch(
                client_ip,
                lat=body.get("latitude"),
                lng=body.get("longitude"),
            )
            self._write_json(
                HTTPStatus.OK,
                {"ok": True, "watchdog": "alive", "ts": int(time.time() * 1000)},
            )
            return

        # ── Test guardian SMS endpoint ───────────────────────────
        if path_only == "/v1/test-guardian-sms":
            try:
                content_len = int(self.headers.get("Content-Length", "0"))
                body = {}
                if content_len > 0:
                    raw = self.rfile.read(content_len)
                    body = json.loads(raw.decode("utf-8"))
            except Exception:
                body = {}

            lat = body.get("latitude")
            lng = body.get("longitude")
            print(f"[remote-v1] Test guardian SMS requested (lat={lat}, lng={lng})")

            ok = send_guardian_alert(latitude=lat, longitude=lng)
            if ok:
                self._write_json(
                    HTTPStatus.OK,
                    {"ok": True, "message": "Test SMS sent to guardian"},
                )
            else:
                self._write_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "ok": False,
                        "error": "sms_failed",
                        "message": "Could not send SMS — check Twilio config and server logs",
                    },
                )
            return

        if path_only != "/v1/analyze-frame":
            self._write_json(
                HTTPStatus.NOT_FOUND,
                {
                    "ok": False,
                    "error": "not_found",
                    "message": "Unknown endpoint",
                },
            )
            return

        if not self._check_api_key():
            self._unauthorized()
            return

        try:
            content_len = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_len = 0

        if content_len <= 0:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": "bad_request",
                    "message": "Request body is required",
                },
            )
            return

        try:
            raw = self.rfile.read(content_len)
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": "bad_json",
                    "message": str(exc),
                },
            )
            return

        try:
            frame_b64 = payload.get("frame_jpeg_base64", "")
            frame_id = payload.get("frame_id")
            include = payload.get("include", {})
            want_phase1 = bool(include.get("phase1", True))
            want_phase2 = bool(include.get("phase2", False))
            phase2 = payload.get("phase2", {}) or {}

            frame, raw_jpeg = _decode_jpeg_and_raw_from_base64(frame_b64, CONFIG.max_jpeg_bytes)

            # ── Touch watchdog (frame = proof of life) ────────────
            client_ip = self.client_address[0]
            _watchdog_touch(
                client_ip,
                lat=payload.get("latitude"),
                lng=payload.get("longitude"),
            )

            with _latest_lock:
                global _latest_frame_jpeg, _latest_frame_ts_ms, _latest_frame_id
                _latest_frame_jpeg = raw_jpeg
                _latest_frame_ts_ms = int(time.time() * 1000)
                _latest_frame_id = str(frame_id) if frame_id is not None else None

            started = time.perf_counter()
            phase1_out = None
            phase2_out = None

            if want_phase1:
                reflex = get_reflex_layer()
                phase1_out = reflex.process_frame(frame)

            if want_phase2:
                mode = _normalize_phase2_mode(str(phase2.get("mode", "caption")))
                context = get_context_layer()
                if mode == "caption":
                    text = context.describe_scene(frame)
                elif mode == "ocr":
                    text = context.read_text(frame)
                else:
                    question = str(phase2.get("question", "")).strip()
                    if not question:
                        raise ValueError("phase2.question is required for mode=vqa")
                    text = context.answer_question(frame, question)

                phase2_out = {
                    "mode": mode,
                    "text": text,
                }

            elapsed_ms = int((time.perf_counter() - started) * 1000)

            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "contract_version": "v1",
                    "frame_id": frame_id,
                    "latency_ms": elapsed_ms,
                    "phase1": phase1_out,
                    "phase2": phase2_out,
                    "ts": int(time.time() * 1000),
                },
            )
        except ValueError as exc:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": "validation_error",
                    "message": str(exc),
                },
            )
        except Exception as exc:
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "ok": False,
                    "error": "server_error",
                    "message": str(exc),
                },
            )

    def log_message(self, fmt: str, *args):
        print(f"[remote-v1] {self.address_string()} - {fmt % args}")


def run():
    _start_watchdog()
    server = ThreadingHTTPServer((CONFIG.host, CONFIG.port), RemoteCameraHandler)
    print("[remote-v1] Standalone contract server started")
    print(f"[remote-v1] Listening on http://{CONFIG.host}:{CONFIG.port}")
    if CONFIG.api_key:
        print("[remote-v1] API key auth enabled (X-API-Key)")
    else:
        print("[remote-v1] API key auth disabled (dev mode)")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[remote-v1] Server stopped")


if __name__ == "__main__":
    run()

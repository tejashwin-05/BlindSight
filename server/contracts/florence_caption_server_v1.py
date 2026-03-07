"""
EcoSight Florence Caption Server (v1)
Standalone, opt-in endpoint for one-shot scene description.

Run this when you only need Florence caption/ocr/vqa and do not want
phase1 object detection pipeline running.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


@dataclass
class ServerConfig:
    host: str = os.getenv("ECOSIGHT_FLORENCE_HOST", "0.0.0.0")
    port: int = int(os.getenv("ECOSIGHT_FLORENCE_PORT", "8090"))
    api_key: str = os.getenv("ECOSIGHT_FLORENCE_API_KEY", "")
    max_jpeg_bytes: int = int(
        os.getenv("ECOSIGHT_FLORENCE_MAX_JPEG_BYTES", str(2 * 1024 * 1024))
    )
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("ECOSIGHT_GROQ_MODEL", "openai/gpt-oss-120b")
    groq_timeout_sec: int = int(os.getenv("ECOSIGHT_GROQ_TIMEOUT_SEC", "12"))
    groq_max_tokens: int = int(os.getenv("ECOSIGHT_GROQ_MAX_TOKENS", "220"))
    groq_enabled: bool = os.getenv("ECOSIGHT_GROQ_ENABLED", "0").strip() not in (
        "0",
        "false",
        "False",
    )


CONFIG = ServerConfig()
_context = None
_model_state_lock = threading.Lock()
_model_ready = False
_model_loading = False
_model_error: str | None = None


def get_context_layer():
    global _context
    if _context is None:
        from phase2_context import ContextLayer

        _context = ContextLayer()
    return _context


def _load_model_now() -> None:
    global _model_ready, _model_loading, _model_error
    with _model_state_lock:
        if _model_ready or _model_loading:
            return
        _model_loading = True
        _model_error = None

    try:
        context = get_context_layer()
        context.load_model()
        with _model_state_lock:
            _model_ready = True
            _model_error = None
    except Exception as exc:
        with _model_state_lock:
            _model_ready = False
            _model_error = str(exc)
        raise
    finally:
        with _model_state_lock:
            _model_loading = False


def _warmup_model_in_background() -> None:
    def _runner() -> None:
        print("[florence-v1] Warming up Florence model...")
        try:
            _load_model_now()
            print("[florence-v1] Florence model ready ✓")
        except Exception as exc:
            print(f"[florence-v1] Florence warmup failed: {exc}")

    threading.Thread(target=_runner, daemon=True).start()


def _get_model_state() -> tuple[bool, bool, str | None]:
    with _model_state_lock:
        return _model_ready, _model_loading, _model_error


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


def _normalize_mode(mode: str) -> str:
    mode = (mode or "").strip().lower()
    if mode in ("caption", "describe", "scene"):
        return "caption"
    if mode in ("ocr", "text"):
        return "ocr"
    if mode in ("vqa", "question", "qa"):
        return "vqa"
    raise ValueError("mode must be one of: caption | ocr | vqa")


def _build_personalization_user_prompt(
    florence_text: str,
    mode: str,
    question: str,
    user_profile: dict,
    context_hint: str,
) -> str:
    profile_json = json.dumps(user_profile or {}, ensure_ascii=False)
    return (
        "You are an accessibility assistant for navigation and scene understanding.\n"
        "Rewrite the Florence output for a user-friendly spoken response.\n"
        "Rules:\n"
        "1) Keep it concise and actionable (max 2 sentences).\n"
        "2) Never invent objects or distances not present in source text.\n"
        "3) Prefer safety-first wording and directional clarity.\n"
        "4) If uncertain, say uncertainty explicitly.\n"
        "5) Output ONLY valid JSON with keys: spoken_text, confidence_note.\n\n"
        f"mode: {mode}\n"
        f"question: {question or ''}\n"
        f"user_profile: {profile_json}\n"
        f"context_hint: {context_hint}\n"
        f"florence_text: {florence_text}\n"
    )


def _try_groq_personalization(
    florence_text: str,
    mode: str,
    question: str,
    user_profile: dict,
    context_hint: str,
) -> tuple[str, bool, str | None]:
    if not CONFIG.groq_enabled:
        return florence_text, False, "groq_disabled"
    if not CONFIG.groq_api_key:
        return florence_text, False, "groq_api_key_missing"

    prompt = _build_personalization_user_prompt(
        florence_text=florence_text,
        mode=mode,
        question=question,
        user_profile=user_profile,
        context_hint=context_hint,
    )

    body = {
        "model": CONFIG.groq_model,
        "temperature": 0.2,
        "max_tokens": CONFIG.groq_max_tokens,
        "messages": [
            {
                "role": "system",
                "content": "Return strict JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
    }

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CONFIG.groq_api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=CONFIG.groq_timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
    except urllib.error.HTTPError as exc:
        return florence_text, False, f"groq_http_{exc.code}"
    except Exception as exc:
        return florence_text, False, f"groq_error:{exc}"

    try:
        content = (
            parsed.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not content:
            return florence_text, False, "groq_empty_content"

        normalized = content
        if normalized.startswith("```"):
            normalized = normalized.strip("`")
            if normalized.startswith("json"):
                normalized = normalized[4:].strip()

        structured = json.loads(normalized)
        spoken_text = str(structured.get("spoken_text", "")).strip()
        if not spoken_text:
            return florence_text, False, "groq_missing_spoken_text"
        return spoken_text, True, None
    except Exception:
        return florence_text, False, "groq_parse_failed"


class FlorenceCaptionHandler(BaseHTTPRequestHandler):
    server_version = "EcoSightFlorenceCaptionV1/1.0"

    def _write_json(self, code: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _check_api_key(self) -> bool:
        if not CONFIG.api_key:
            return True
        header_key = self.headers.get("X-API-Key", "")
        return header_key == CONFIG.api_key

    def _unauthorized(self):
        self._write_json(
            HTTPStatus.UNAUTHORIZED,
            {
                "ok": False,
                "error": "unauthorized",
                "message": "Missing or invalid X-API-Key",
            },
        )

    def do_GET(self):
        if self.path == "/health":
            ready, loading, error = _get_model_state()
            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "service": "ecosight-florence-caption-v1",
                    "model_ready": ready,
                    "model_loading": loading,
                    "model_error": error,
                    "personalization_available": bool(
                        CONFIG.groq_enabled and CONFIG.groq_api_key
                    ),
                    "groq_model": CONFIG.groq_model,
                    "ts": int(time.time() * 1000),
                },
            )
            return

        self._write_json(
            HTTPStatus.NOT_FOUND,
            {
                "ok": False,
                "error": "not_found",
                "message": "Use GET /health or POST /v1/describe-scene",
            },
        )

    def do_POST(self):
        if self.path not in (
            "/v1/describe-scene",
            "/v1/describe-scene-personalized",
        ):
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
            ready, loading, error = _get_model_state()
            if not ready:
                self._write_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "ok": False,
                        "error": "warming_up" if loading else "model_not_ready",
                        "message": (
                            "Florence model is warming up. Try again in 10-30 seconds."
                            if loading
                            else (error or "Florence model is not ready")
                        ),
                    },
                )
                return

            frame_b64 = payload.get("frame_jpeg_base64", "")
            mode = _normalize_mode(str(payload.get("mode", "caption")))
            question = str(payload.get("question", "")).strip()
            personalize = payload.get("personalize", {}) or {}
            force_personalized = self.path == "/v1/describe-scene-personalized"
            personalize_enabled = bool(personalize.get("enabled", force_personalized))
            user_profile = personalize.get("user_profile", {}) or {}
            if not isinstance(user_profile, dict):
                raise ValueError("personalize.user_profile must be an object")
            context_hint = str(personalize.get("context_hint", "")).strip()

            frame = _decode_jpeg_from_base64(frame_b64, CONFIG.max_jpeg_bytes)

            started = time.perf_counter()
            context = get_context_layer()
            if mode == "caption":
                text = context.describe_scene(frame)
            elif mode == "ocr":
                text = context.read_text(frame)
            else:
                if not question:
                    raise ValueError("question is required for mode=vqa")
                text = context.answer_question(frame, question)

            final_text = text
            used_reasoner = False
            reasoner_status = None
            if personalize_enabled:
                final_text, used_reasoner, reasoner_status = _try_groq_personalization(
                    florence_text=text,
                    mode=mode,
                    question=question,
                    user_profile=user_profile,
                    context_hint=context_hint,
                )

            elapsed_ms = int((time.perf_counter() - started) * 1000)

            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "mode": mode,
                    "text": final_text,
                    "source": "groq_augmented" if used_reasoner else "florence_raw",
                    "personalize_enabled": personalize_enabled,
                    "reasoner_used": used_reasoner,
                    "reasoner_status": reasoner_status,
                    "latency_ms": elapsed_ms,
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
        print(f"[florence-v1] {self.address_string()} - {fmt % args}")


def run():
    server = ThreadingHTTPServer((CONFIG.host, CONFIG.port), FlorenceCaptionHandler)
    print("[florence-v1] Standalone Florence caption server started")
    print(f"[florence-v1] Listening on http://{CONFIG.host}:{CONFIG.port}")
    if CONFIG.api_key:
        print("[florence-v1] API key auth enabled (X-API-Key)")
    else:
        print("[florence-v1] API key auth disabled (dev mode)")

    _warmup_model_in_background()
    print("[florence-v1] Model warmup started; check /health for model_ready=true")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[florence-v1] Server stopped")


if __name__ == "__main__":
    run()

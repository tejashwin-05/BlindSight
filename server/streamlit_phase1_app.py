"""
BlindSight Phase 1 Streamlit Dashboard
Replaces OpenCV judge window with a web UI:
- live annotated camera feed
- active hazard card
- recent alert timeline
- browser-side TTS for hazard guidance
"""

from __future__ import annotations

import json
import time
import os
import subprocess
import sys
import atexit
import base64
from typing import Any

import cv2
import numpy as np
import streamlit as st

import config
from camera import CameraManager
from debounce import HazardDebouncer
from phase1_reflex import ReflexLayer
from phase1_freespace import FreeSpaceEstimator
from phase2_context import ContextLayer


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


def _is_in_forward_path_zone(box: list[int], frame_shape: tuple[int, int, int]) -> bool:
    frame_h, frame_w = frame_shape[0], frame_shape[1]
    x1, y1, x2, y2 = box
    center_x = (x1 + x2) / 2.0
    center_ratio = center_x / max(frame_w, 1)
    bottom_ratio = y2 / max(frame_h, 1)

    in_lane = config.PATH_ZONE_X_START <= center_ratio <= config.PATH_ZONE_X_END
    near_ground = bottom_ratio >= config.PATH_ZONE_MIN_BOTTOM_Y_RATIO
    return in_lane and near_ground


def _preprocess_path_detections(detections: list[dict], frame_shape: tuple[int, int, int]) -> list[dict]:
    filtered = [
        d
        for d in detections
        if _is_in_forward_path_zone(d["box"], frame_shape)
        and config.DETECTION_MIN_DISTANCE_M <= d["distance"] <= config.DETECTION_MAX_DISTANCE_M
    ]
    filtered.sort(key=lambda d: d["distance"])

    merged: list[dict] = []
    for det in filtered:
        det_center = _box_center(det["box"])
        duplicate = False
        for kept in merged:
            kept_center = _box_center(kept["box"])
            center_delta = abs(det_center[0] - kept_center[0]) + abs(det_center[1] - kept_center[1])
            overlap = _box_iou(det["box"], kept["box"])
            if (
                overlap >= config.DETECTION_MERGE_IOU_THRESHOLD
                or center_delta <= config.DETECTION_MERGE_CENTER_DISTANCE_PX
            ):
                duplicate = True
                break
        if not duplicate:
            merged.append(det)

    return merged


def _match_target_detection(detections: list[dict], tracked: dict) -> dict | None:
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


def _init_state() -> None:
    simple_defaults: dict[str, Any] = {
        "running": False,
        "camera_opened": False,
        "camera_index": 0,                      # added: camera device index
        "last_detections": [],
        "latest_frame": None,
        "stream_frame_counter": 0,
        "tracked_target": None,
        "tracked_lost_frames": 0,
        "switch_candidate": None,
        "switch_candidate_frames": 0,
        "last_alert": None,
        "phase2_description": "",
        "phase2_request": False,
        "last_tts_msg": "",
        "alert_log": [],
        "last_error": "",
        "backend_proc": None,
        "backend_running": False,
    }
    for key, value in simple_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "camera" not in st.session_state:
        st.session_state["camera"] = CameraManager()
    if "reflex" not in st.session_state:
        st.session_state["reflex"] = ReflexLayer()
    if "debouncer" not in st.session_state:
        st.session_state["debouncer"] = HazardDebouncer()
    if "context" not in st.session_state:
        st.session_state["context"] = None


def _get_context() -> ContextLayer:
    ctx = st.session_state.get("context")
    if ctx is None:
        ctx = ContextLayer()
        st.session_state["context"] = ctx
    return ctx


def _start_backend() -> None:
    proc = st.session_state.get("backend_proc")
    if proc is not None and proc.poll() is None:
        st.session_state["backend_running"] = True
        return

    env = os.environ.copy()
    env["ECOSIGHT_HEADLESS"] = "1"
    env["ECOSIGHT_SERVER_ONLY"] = "1"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "main.py")
    try:
        backend = subprocess.Popen(
            [sys.executable, main_py],
            cwd=script_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        st.session_state["backend_proc"] = backend
        st.session_state["backend_running"] = True
        st.session_state["last_error"] = ""   # clear any previous error
    except Exception as e:
        st.session_state["last_error"] = f"Failed to start backend: {e}"
        st.session_state["backend_running"] = False


def _stop_backend() -> None:
    proc = st.session_state.get("backend_proc")
    if proc is None:
        st.session_state["backend_running"] = False
        return

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
    st.session_state["backend_running"] = False
    st.session_state["backend_proc"] = None


def _cleanup_backend() -> None:
    try:
        _stop_backend()
    except Exception:
        pass


atexit.register(_cleanup_backend)


def _draw_frame(frame: np.ndarray, detections: list[dict], path_detections: list[dict], active_target: dict | None) -> np.ndarray:
    vis = frame.copy()

    path_keys = {
        (d["box"][0], d["box"][1], d["box"][2], d["box"][3]) for d in path_detections
    }

    for det in detections:
        x1, y1, x2, y2 = det["box"]
        key = (x1, y1, x2, y2)
        is_path = key in path_keys
        color = (120, 120, 120)
        thickness = 1

        if is_path:
            color = (255, 170, 0)
            thickness = 2

        if active_target is not None and det.get("track_id") == active_target.get("track_id"):
            color = (0, 0, 255)
            thickness = 3

        label = f"{det['hazard']} {det['distance']}m"
        if det.get("track_id") is not None:
            label += f" id:{det['track_id']}"

        cv2.rectangle(vis, (x1, y1), (x2, y2), color, thickness)
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(vis, (x1, max(0, y1 - 20)), (x1 + w, y1), color, -1)
        cv2.putText(vis, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    h, w = vis.shape[:2]
    lx1 = int(w * config.PATH_ZONE_X_START)
    lx2 = int(w * config.PATH_ZONE_X_END)
    ly = int(h * config.PATH_ZONE_MIN_BOTTOM_Y_RATIO)
    cv2.rectangle(vis, (lx1, ly), (lx2, h - 1), (0, 255, 0), 2)

    return vis


def _build_freespace_heatmap(frame_shape: tuple[int, int, int], detections: list[dict]) -> np.ndarray:
    """
    Build a pixel-level free-space heatmap overlay.
    Green = safe/empty space, Red = occupied/hazard zone.
    Returns an RGB image of the same size as the frame.
    """
    h, w = frame_shape[0], frame_shape[1]
    y_min = int(h * config.GUIDANCE_LOWER_FRAME_START_RATIO)

    # Start with a full green canvas (safe)
    heatmap = np.zeros((h, w, 3), dtype=np.uint8)
    heatmap[:, :] = (0, 180, 0)  # green = free

    # Upper region (above path zone) — neutral grey
    heatmap[:y_min, :] = (60, 60, 60)

    # Paint hazard boxes red with a soft radial falloff
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)

        # Core box — full red
        heatmap[y1:y2, x1:x2] = (200, 0, 0)

        # Soft danger margin around the box
        margin = 20
        mx1, my1 = max(0, x1 - margin), max(y_min, y1 - margin)
        mx2, my2 = min(w - 1, x2 + margin), min(h - 1, y2 + margin)
        for py in range(my1, my2):
            for px in range(mx1, mx2):
                if y1 <= py <= y2 and x1 <= px <= x2:
                    continue  # already red
                # blend orange into the margin
                existing = heatmap[py, px]
                if not np.array_equal(existing, np.array([200, 0, 0])):
                    heatmap[py, px] = (
                        min(255, int(existing[0] * 0.4 + 220 * 0.6)),
                        min(255, int(existing[1] * 0.4 + 120 * 0.6)),
                        0,
                    )

    # Draw lane dividers
    lx_left = int(w * config.LEFT_ZONE_END)
    lx_right = int(w * config.RIGHT_ZONE_START)
    cv2.line(heatmap, (lx_left, y_min), (lx_left, h - 1), (255, 255, 255), 1)
    cv2.line(heatmap, (lx_right, y_min), (lx_right, h - 1), (255, 255, 255), 1)

    # Lane safety scores
    freespace = FreeSpaceEstimator("heuristic")
    scores = freespace.lane_scores(frame_shape, detections)
    lane_labels = {
        "left":   (int(w * 0.10), int(h * 0.92)),
        "center": (int(w * 0.42), int(h * 0.92)),
        "right":  (int(w * 0.72), int(h * 0.92)),
    }
    for lane, pos in lane_labels.items():
        score = scores.get(lane, 1.0)
        pct = int(score * 100)
        color = (0, 220, 0) if score >= 0.6 else (220, 180, 0) if score >= 0.3 else (220, 30, 30)
        cv2.putText(heatmap, f"{lane} {pct}%", pos, cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    # Legend
    cv2.putText(heatmap, "Free-Space Heatmap", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(heatmap, "GREEN=safe  ORANGE=caution  RED=hazard", (8, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1)

    return heatmap


def _frame_to_data_uri(frame_rgb: np.ndarray, quality: int = 65) -> str:
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return ""
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _maybe_speak_browser(text: str, enabled: bool) -> None:
    if not enabled or not text:
        return
    if text == st.session_state.get("last_tts_msg", ""):
        return

    st.session_state["last_tts_msg"] = text
    payload = json.dumps(text)
    st.components.v1.html(
        f"""
        <script>
          const msg = {payload};
          window.speechSynthesis.cancel();
          const utter = new SpeechSynthesisUtterance(msg);
          utter.rate = 1.0;
          utter.pitch = 1.0;
          utter.volume = 1.0;
          window.speechSynthesis.speak(utter);
        </script>
        """,
        height=0,
    )


def _compute_active_target(path_detections: list[dict]) -> dict | None:
    tracked_target = st.session_state["tracked_target"]
    tracked_lost_frames = st.session_state["tracked_lost_frames"]
    switch_candidate = st.session_state["switch_candidate"]
    switch_candidate_frames = st.session_state["switch_candidate_frames"]

    if not path_detections:
        st.session_state["tracked_target"] = None
        st.session_state["tracked_lost_frames"] = 0
        st.session_state["switch_candidate"] = None
        st.session_state["switch_candidate_frames"] = 0
        return None

    if tracked_target is None:
        selected = path_detections[0]
        st.session_state["tracked_target"] = {
            **selected,
            "was_near": selected["distance"] <= config.NEAR_HAZARD_DISTANCE_M,
        }
        st.session_state["tracked_lost_frames"] = 0
        return st.session_state["tracked_target"]

    matched = _match_target_detection(path_detections, tracked_target)
    if matched is not None:
        st.session_state["tracked_lost_frames"] = 0
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
                    st.session_state["tracked_target"] = {
                        **next_target,
                        "was_near": next_target["distance"] <= config.NEAR_HAZARD_DISTANCE_M,
                    }
                    st.session_state["switch_candidate"] = None
                    st.session_state["switch_candidate_frames"] = 0
                else:
                    st.session_state["switch_candidate"] = switch_candidate
                    st.session_state["switch_candidate_frames"] = switch_candidate_frames
            else:
                st.session_state["tracked_target"] = None
                st.session_state["switch_candidate"] = None
                st.session_state["switch_candidate_frames"] = 0
        else:
            st.session_state["tracked_target"] = {**matched, "was_near": was_near}
            st.session_state["switch_candidate"] = None
            st.session_state["switch_candidate_frames"] = 0

        return st.session_state["tracked_target"]

    tracked_lost_frames += 1
    st.session_state["tracked_lost_frames"] = tracked_lost_frames
    if tracked_lost_frames >= config.TARGET_LOST_FRAMES_TO_SWITCH:
        selected = path_detections[0]
        st.session_state["tracked_target"] = {
            **selected,
            "was_near": selected["distance"] <= config.NEAR_HAZARD_DISTANCE_M,
        }
        st.session_state["tracked_lost_frames"] = 0
        st.session_state["switch_candidate"] = None
        st.session_state["switch_candidate_frames"] = 0

    return st.session_state["tracked_target"]


def _build_message(target: dict) -> str:
    if target["distance"] <= config.NEAR_HAZARD_DISTANCE_M:
        msg = (
            f"Hazard near: {target['hazard']} on your {target['direction']}, "
            f"{target['distance']} meters"
        )
    else:
        msg = (
            f"Next object: {target['hazard']} on your {target['direction']}, "
            f"{target['distance']} meters"
        )

    guidance = target.get("guidance", "")
    if guidance:
        msg = f"{msg}. {guidance}."
    return msg


def main() -> None:
    st.set_page_config(page_title="BlindSight", layout="wide")
    _init_state()

    # Do NOT start backend automatically – let user control it
    # _start_backend()   <--- removed

    st.title("BlindSight Dashboard")

    left, right = st.columns([3, 2])
    with right:
        st.subheader("Controls")
        tts_enabled = st.toggle("Enable Browser TTS", value=True)
        auto_refresh_ms = st.slider("Refresh interval (ms)", min_value=80, max_value=500, value=220, step=20)
        infer_every_n = st.slider("Run detection every N processed frames", min_value=1, max_value=4, value=2, step=1)

        # Camera index selection
        cam_index = st.number_input("Camera index", min_value=0, max_value=10, value=st.session_state["camera_index"], step=1)
        if cam_index != st.session_state["camera_index"]:
            st.session_state["camera_index"] = cam_index
            # If camera is already opened, we need to reopen with new index
            if st.session_state["camera_opened"]:
                st.session_state["camera"].release()
                st.session_state["camera_opened"] = False
                st.session_state["running"] = False
                st.warning("Camera index changed. Please click Start again.")

        st.caption(f"Backend main.py: {'Running' if st.session_state.get('backend_running') else 'Stopped'}")

        backend_col1, backend_col2 = st.columns(2)
        with backend_col1:
            if st.button("Start Backend"):
                _start_backend()
        with backend_col2:
            if st.button("Stop Backend"):
                _stop_backend()

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("Start"):
                # Attempt to open camera with error handling
                try:
                    if not st.session_state["camera_opened"]:
                        # Set camera index before opening
                        st.session_state["camera"].set_index(st.session_state["camera_index"])
                        st.session_state["camera"].open()
                        st.session_state["camera_opened"] = True
                    st.session_state["running"] = True
                    st.session_state["last_error"] = ""
                except Exception as e:
                    st.session_state["last_error"] = f"Failed to open camera: {e}"
                    st.session_state["camera_opened"] = False
                    st.session_state["running"] = False

        with btn_col2:
            if st.button("Stop"):
                st.session_state["running"] = False
                if st.session_state["camera_opened"]:
                    st.session_state["camera"].release()
                    st.session_state["camera_opened"] = False

        if st.button("Describe Scene (Phase 2)"):
            st.session_state["phase2_request"] = True

        st.caption(f"Running: {'Yes' if st.session_state['running'] else 'No'}")
        if st.session_state["last_error"]:
            st.error(st.session_state["last_error"])

        st.subheader("Current Hazard")
        current_hazard_box = st.empty()

        st.subheader("Recent Alerts")
        alert_box = st.empty()

        st.subheader("Scene Description")
        desc_box = st.empty()

    with left:
        frame_box = st.empty()
        st.caption("Free-Space Heatmap")
        heatmap_box = st.empty()

    if not st.session_state["running"]:
        frame_box.info("Click Start to run live camera stream.")
        if st.session_state["alert_log"]:
            alert_box.table(st.session_state["alert_log"][:8])
        return

    try:
        # Read frame with error handling
        try:
            result = st.session_state["camera"].read()
            if result is None:
                st.session_state["last_error"] = "Camera returned no frame"
                time.sleep(auto_refresh_ms / 1000.0)
                st.rerun()
                return
            # Expecting a tuple (should_process, frame)
            if isinstance(result, tuple) and len(result) == 2:
                should_process, frame = result
            else:
                # Fallback if read() returns only frame
                frame = result
                should_process = True
        except Exception as e:
            st.session_state["last_error"] = f"Camera read error: {e}"
            time.sleep(auto_refresh_ms / 1000.0)
            st.rerun()
            return

        if frame is None:
            st.session_state["last_error"] = "Camera frame not available"
            time.sleep(auto_refresh_ms / 1000.0)
            st.rerun()
            return

        st.session_state["latest_frame"] = frame.copy()

        if st.session_state.get("phase2_request", False):
            st.session_state["phase2_request"] = False
            try:
                with st.spinner("Describing scene with Florence-2..."):
                    ctx = _get_context()
                    description = ctx.describe_scene(st.session_state["latest_frame"])
                st.session_state["phase2_description"] = description
                if tts_enabled and description:
                    _maybe_speak_browser(description, True)
            except Exception as e:
                st.session_state["phase2_description"] = f"Phase 2 error: {e}"

        detections = st.session_state["last_detections"]
        path_detections: list[dict] = []
        active_target: dict | None = st.session_state["tracked_target"]

        if should_process:
            st.session_state["stream_frame_counter"] += 1
            run_inference = (st.session_state["stream_frame_counter"] % infer_every_n == 0)

            if run_inference:
                detections = st.session_state["reflex"].process_frame(frame)
                st.session_state["last_detections"] = detections
                path_detections = _preprocess_path_detections(detections, frame.shape)
                active_target = _compute_active_target(path_detections)
            else:
                detections = st.session_state["last_detections"]

            if run_inference and active_target and st.session_state["debouncer"].should_alert(active_target["hazard"], active_target["distance"]):
                msg = _build_message(active_target)
                st.session_state["last_alert"] = msg
                st.session_state["alert_log"].insert(
                    0,
                    {
                        "time": time.strftime("%H:%M:%S"),
                        "hazard": active_target["hazard"],
                        "direction": active_target["direction"],
                        "distance_m": active_target["distance"],
                        "action": active_target.get("guidance", ""),
                    },
                )
                st.session_state["alert_log"] = st.session_state["alert_log"][:40]
                _maybe_speak_browser(msg, tts_enabled)

        if not path_detections and detections:
            path_detections = _preprocess_path_detections(detections, frame.shape)

        vis = _draw_frame(frame, detections, path_detections, active_target)
        vis = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
        data_uri = _frame_to_data_uri(vis, quality=65)
        if data_uri:
            frame_box.markdown(
                f"<img src=\"{data_uri}\" style=\"width:100%;height:auto;border-radius:8px;\"/>",
                unsafe_allow_html=True,
            )
        else:
            frame_box.warning("Frame encode failed")

        # Free-space heatmap
        heatmap = _build_freespace_heatmap(frame.shape, detections)
        heatmap_uri = _frame_to_data_uri(heatmap, quality=80)
        if heatmap_uri:
            heatmap_box.markdown(
                f"<img src=\"{heatmap_uri}\" style=\"width:100%;height:auto;border-radius:8px;\"/>",
                unsafe_allow_html=True,
            )

        if active_target:
            current_hazard_box.success(
                (
                    f"{active_target['hazard']} | {active_target['distance']} m | "
                    f"{active_target['direction']} | {active_target.get('guidance', '')}"
                )
            )
        else:
            current_hazard_box.info("No active hazard in path zone")

        if st.session_state["alert_log"]:
            alert_box.table(st.session_state["alert_log"][:8])
        else:
            alert_box.info("No alerts yet")

        if st.session_state.get("phase2_description"):
            desc_box.info(st.session_state["phase2_description"])
        else:
            desc_box.info("Press 'Describe Scene (Phase 2)' to capture and describe the current frame")

    except Exception as e:
        st.session_state["last_error"] = str(e)
        st.error(f"Runtime error: {e}")
    finally:
        time.sleep(auto_refresh_ms / 1000.0)
        st.rerun()


if __name__ == "__main__":
    main()
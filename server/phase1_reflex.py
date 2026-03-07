"""
EcoSight Phase 1 — Reflex Layer
Real-time hazard detection, depth estimation, and directionality.
"""

import cv2
import torch
import numpy as np
from ultralytics import YOLO
import config
from phase1_depth import DepthEstimator
from phase1_tracker import TrackManager
from phase1_freespace import FreeSpaceEstimator
from phase1_guidance import PathGuidance

# ─── PyTorch 2.6+ Safe Loading Fix ───────────────────────────
# PyTorch 2.6+ defaults to weights_only=True, breaking YOLOv8 loading.
# We monkey-patch torch.load to revert to old behavior (weights_only=False).
_original_load = torch.load

def _patched_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)

torch.load = _patched_load
# ─────────────────────────────────────────────────────────────


class ReflexLayer:
    """Continuous real-time hazard detection engine."""

    def __init__(self):
        print("[Phase1] Loading YOLOv8 model...")
        self.model = YOLO(config.YOLO_MODEL)
        self.focal_constant = config.FOCAL_CONSTANT
        self.confidence_threshold = config.YOLO_CONFIDENCE_THRESHOLD
        self.hazard_classes = config.HAZARD_CLASSES
        self.device = 0 if torch.cuda.is_available() else "cpu"
        self.imgsz = config.PHASE1_IMGSZ
        self.max_det = config.PHASE1_MAX_DETECTIONS

        self.depth = DepthEstimator(config.PHASE1_DEPTH_BACKEND, self.focal_constant)
        self.tracker = TrackManager(config.PHASE1_TRACKER_BACKEND)
        self.freespace = FreeSpaceEstimator(config.PHASE1_FREE_SPACE_BACKEND)
        self.guidance = PathGuidance()
        print("[Phase1] YOLOv8 model loaded ✓")

    # ── Public API ─────────────────────────────────────────────
    def process_frame(self, frame: np.ndarray) -> list[dict]:
        """
        Process a single frame and return a list of detected hazards.
        Each hazard dict:
            { "hazard": str, "direction": str, "distance": float, "confidence": float }
        """
        results = self.model(
            frame,
            verbose=False,
            conf=self.confidence_threshold,
            imgsz=self.imgsz,
            max_det=self.max_det,
            device=self.device,
        )
        detections: list[dict] = []
        raw_boxes: list[list[int]] = []
        raw_meta: list[tuple[str, str, float]] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                if cls_id not in self.hazard_classes:
                    continue

                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                hazard_name = self.hazard_classes[cls_id]
                direction = self._get_direction(x1, x2, frame.shape[1])
                raw_boxes.append([int(x1), int(y1), int(x2), int(y2)])
                raw_meta.append((hazard_name, direction, conf))

        if not raw_boxes:
            return []

        distances = self.depth.estimate_distances(frame, raw_boxes)
        for idx, box in enumerate(raw_boxes):
            hazard_name, direction, conf = raw_meta[idx]
            detections.append({
                "hazard": hazard_name,
                "direction": direction,
                "distance": round(float(distances[idx]), 1),
                "confidence": round(float(conf), 2),
                "box": box,
            })

        # Assign stable track IDs
        detections = self.tracker.assign_ids(detections)

        # Free-space + guidance phrase per detection
        lane_scores = self.freespace.lane_scores(frame.shape, detections)
        for det in detections:
            move_lane, guidance_text = self.guidance.choose_move(det["direction"], lane_scores)
            det["recommended_lane"] = move_lane
            det["guidance"] = guidance_text

        # Sort by distance — closest hazard first
        detections.sort(key=lambda d: d["distance"])
        return detections

    # ── Private Helpers ────────────────────────────────────────
    def _get_direction(self, x1: float, x2: float, frame_width: int) -> str:
        """Map bounding box centre x to Left / Center / Right."""
        center_x = (x1 + x2) / 2
        ratio = center_x / frame_width
        if ratio < config.LEFT_ZONE_END:
            return "left"
        elif ratio > config.RIGHT_ZONE_START:
            return "right"
        else:
            return "center"

    def _estimate_distance(self, y1: float, y2: float) -> float:
        """Monocular depth via bounding‐box height heuristic."""
        pixel_height = max(y2 - y1, 1)  # avoid div-by-zero
        distance = self.focal_constant / pixel_height
        return max(distance, 0.3)  # clamp minimum 0.3 m

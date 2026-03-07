"""
EcoSight Phase 1 — Depth Estimation Module
Supports:
- heuristic distance (fast, stable)
- Depth Anything V2 Small (optional)
"""

from __future__ import annotations

import cv2
import numpy as np
import torch
from PIL import Image

import config


class DepthEstimator:
    def __init__(self, backend: str, focal_constant: float):
        self.backend = backend
        self.focal_constant = focal_constant
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._processor = None
        self._model = None
        self._ready = False

        if self.backend == "depth_anything_v2_small":
            self._try_load_depth_anything()

    def _try_load_depth_anything(self) -> None:
        try:
            import importlib

            transformers_mod = importlib.import_module("transformers")
            AutoImageProcessor = getattr(transformers_mod, "AutoImageProcessor")
            AutoModelForDepthEstimation = getattr(transformers_mod, "AutoModelForDepthEstimation")

            self._processor = AutoImageProcessor.from_pretrained(config.DEPTH_ANYTHING_MODEL_ID)
            self._model = AutoModelForDepthEstimation.from_pretrained(config.DEPTH_ANYTHING_MODEL_ID).to(self.device)
            self._model.eval()
            self._ready = True
            print("[Phase1][Depth] Depth Anything V2 Small loaded ✓")
        except Exception as e:
            self.backend = "heuristic"
            self._ready = False
            print(f"[Phase1][Depth] Falling back to heuristic depth: {e}")

    def _heuristic_distance(self, y1: float, y2: float) -> float:
        pixel_height = max(y2 - y1, 1)
        distance = self.focal_constant / pixel_height
        return max(distance, config.DETECTION_MIN_DISTANCE_M)

    def _depth_map(self, frame: np.ndarray) -> np.ndarray | None:
        if not self._ready or self._processor is None or self._model is None:
            return None
        try:
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            inputs = self._processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                out = self._model(**inputs)
                pred = out.predicted_depth
            depth = pred.squeeze().detach().cpu().numpy()
            if depth.ndim != 2:
                return None
            depth = cv2.resize(depth, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_CUBIC)
            return depth
        except Exception as e:
            print(f"[Phase1][Depth] Depth map inference failed, fallback heuristic: {e}")
            return None

    def estimate_distances(self, frame: np.ndarray, raw_boxes: list[list[int]]) -> list[float]:
        """
        Returns a distance list for each input box.
        """
        if self.backend != "depth_anything_v2_small":
            return [self._heuristic_distance(b[1], b[3]) for b in raw_boxes]

        depth_map = self._depth_map(frame)
        if depth_map is None:
            return [self._heuristic_distance(b[1], b[3]) for b in raw_boxes]

        distances: list[float] = []
        for box in raw_boxes:
            x1, y1, x2, y2 = box
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1] - 1, x2)
            y2 = min(frame.shape[0] - 1, y2)
            patch = depth_map[y1:y2 + 1, x1:x2 + 1]
            if patch.size == 0:
                distances.append(self._heuristic_distance(y1, y2))
                continue

            dval = float(np.median(patch))
            dval = max(dval, config.DEPTH_MIN_VALUE)
            est = config.DEPTH_DISTANCE_SCALE / dval
            est = max(config.DETECTION_MIN_DISTANCE_M, min(config.DETECTION_MAX_DISTANCE_M, est))
            distances.append(est)

        return distances

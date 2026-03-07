"""
EcoSight Phase 1 — Free-space Module
Current backend:
- heuristic lane occupancy from hazard boxes
"""

from __future__ import annotations

import config


class FreeSpaceEstimator:
    def __init__(self, backend: str):
        self.backend = backend
        if self.backend in ("bisenetv2", "fast_scnn"):
            print(f"[Phase1][FreeSpace] {self.backend} requested; using heuristic backend currently")
            self.backend = "heuristic"

    def lane_scores(self, frame_shape: tuple[int, int, int], detections: list[dict]) -> dict[str, float]:
        """
        Returns free-space score per lane in [0,1]: left/center/right.
        Higher = safer/more open.
        """
        height, width = frame_shape[0], frame_shape[1]
        y_min = int(height * config.GUIDANCE_LOWER_FRAME_START_RATIO)
        y_max = height

        lane_bounds = {
            "left": (0, int(width * config.LEFT_ZONE_END)),
            "center": (int(width * config.LEFT_ZONE_END), int(width * config.RIGHT_ZONE_START)),
            "right": (int(width * config.RIGHT_ZONE_START), width),
        }

        occupied = {"left": 0.0, "center": 0.0, "right": 0.0}

        for det in detections:
            x1, y1, x2, y2 = det["box"]
            y1c = max(y_min, y1)
            y2c = min(y_max, y2)
            if y2c <= y1c:
                continue

            for lane, (lx1, lx2) in lane_bounds.items():
                ix1 = max(x1, lx1)
                ix2 = min(x2, lx2)
                if ix2 <= ix1:
                    continue
                area = float((ix2 - ix1) * (y2c - y1c))
                occupied[lane] += area

        scores: dict[str, float] = {}
        lane_height = max(1, y_max - y_min)
        for lane, (lx1, lx2) in lane_bounds.items():
            lane_area = max(1.0, float((lx2 - lx1) * lane_height))
            occ_ratio = min(1.0, occupied[lane] / lane_area)
            scores[lane] = max(0.0, 1.0 - occ_ratio)

        return scores

"""
EcoSight Phase 1 — Tracking Module
Backends:
- bytetrack (Ultralytics built-in)
- simple (lightweight center matching)
- ocsort (falls back to simple unless external integration is added)
"""

from __future__ import annotations

from dataclasses import dataclass

import config


@dataclass
class _TrackItem:
    track_id: int
    center_x: float
    center_y: float
    age: int


class TrackManager:
    def __init__(self, backend: str):
        self.backend = backend
        self._next_id = 1
        self._tracks: dict[int, _TrackItem] = {}

        if self.backend == "ocsort":
            print("[Phase1][Track] OC-SORT backend requested; using simple fallback currently")
            self.backend = "simple"

    @staticmethod
    def _center(box: list[int]) -> tuple[float, float]:
        x1, y1, x2, y2 = box
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def assign_ids(self, detections: list[dict]) -> list[dict]:
        """
        Assign stable track_id to detections (simple fallback tracker).
        """
        if not detections:
            self._age_tracks()
            return detections

        used_track_ids: set[int] = set()

        for det in detections:
            cx, cy = self._center(det["box"])
            best_id = None
            best_delta = float("inf")

            for tid, track in self._tracks.items():
                if tid in used_track_ids:
                    continue
                delta = abs(cx - track.center_x) + abs(cy - track.center_y)
                if delta < best_delta:
                    best_delta = delta
                    best_id = tid

            if best_id is not None and best_delta <= config.TRACK_MATCH_MAX_CENTER_DELTA_PX:
                track = self._tracks[best_id]
                track.center_x = cx
                track.center_y = cy
                track.age = 0
                det["track_id"] = best_id
                used_track_ids.add(best_id)
            else:
                tid = self._next_id
                self._next_id += 1
                self._tracks[tid] = _TrackItem(track_id=tid, center_x=cx, center_y=cy, age=0)
                det["track_id"] = tid
                used_track_ids.add(tid)

        self._age_tracks(except_ids=used_track_ids)
        return detections

    def _age_tracks(self, except_ids: set[int] | None = None) -> None:
        except_ids = except_ids or set()
        stale_ids: list[int] = []
        for tid, track in self._tracks.items():
            if tid not in except_ids:
                track.age += 1
            if track.age > config.TRACK_MAX_AGE_FRAMES:
                stale_ids.append(tid)
        for tid in stale_ids:
            self._tracks.pop(tid, None)

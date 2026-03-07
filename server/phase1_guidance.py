"""
EcoSight Phase 1 — Path Guidance Module
Chooses safer move lane based on hazard direction + free-space map.
"""

from __future__ import annotations

import config


class PathGuidance:
    @staticmethod
    def _lane_order_away_from_hazard(hazard_direction: str) -> list[str]:
        if hazard_direction == "left":
            return ["right", "center", "left"]
        if hazard_direction == "right":
            return ["left", "center", "right"]
        return ["left", "right", "center"]

    def choose_move(self, hazard_direction: str, lane_scores: dict[str, float]) -> tuple[str, str]:
        """
        Returns tuple: (move_lane, phrase)
        Example: ('left', 'move slightly left')
        """
        order = self._lane_order_away_from_hazard(hazard_direction)
        best_lane = max(order, key=lambda lane: lane_scores.get(lane, 0.0))
        phrase = f"move {config.GUIDANCE_MOVE_WORD} {best_lane}"
        return best_lane, phrase

"""
EcoSight — Debounce / Anti-Spam Layer
Prevents the same hazard warning from firing repeatedly,
which would cause TTS to talk over itself and overwhelm the user.
"""

import time
import config


class HazardDebouncer:
    """
    Per‑hazard cooldown timer.

    Rule: After warning about hazard X, suppress further warnings
    about hazard X for `DEBOUNCE_COOLDOWN_SEC` seconds — UNLESS
    the distance changes significantly (user is getting closer).

    Also implements a global minimum interval so the phone never
    receives more than one alert in any given time window.
    """

    def __init__(self):
        # { "hazard_name": { "last_time": float, "last_dist": float } }
        self._history: dict[str, dict] = {}
        self._global_last_time: float = 0.0
        self.cooldown = config.DEBOUNCE_COOLDOWN_SEC
        self.global_min_interval = config.DEBOUNCE_GLOBAL_MIN_SEC
        self.distance_change_threshold = config.DEBOUNCE_DISTANCE_CHANGE

    def should_alert(self, hazard: str, distance: float) -> bool:
        """
        Returns True if this hazard should be announced to the user.

        Args:
            hazard:   hazard class name (e.g. "person", "puddle")
            distance: estimated distance in metres
        """
        now = time.monotonic()

        # ── Global rate‑limit ─────────────────────────────────
        if now - self._global_last_time < self.global_min_interval:
            return False

        # ── Per‑hazard cooldown ───────────────────────────────
        if hazard in self._history:
            entry = self._history[hazard]
            elapsed = now - entry["last_time"]
            dist_delta = abs(distance - entry["last_dist"])

            # Still within cooldown AND distance hasn't changed much
            if elapsed < self.cooldown and dist_delta < self.distance_change_threshold:
                return False

        # ── Allow alert — update history ──────────────────────
        self._history[hazard] = {"last_time": now, "last_dist": distance}
        self._global_last_time = now
        return True

    def reset(self) -> None:
        """Clear all cooldown history (e.g. when switching modes)."""
        self._history.clear()
        self._global_last_time = 0.0

"""
EcoSight — Camera Manager
Handles webcam capture with frame skipping to maintain target FPS
and prevent laptop overheating.
"""

import cv2
import time
import config


class CameraManager:
    """
    Wraps OpenCV VideoCapture with intelligent frame skipping.

    Only yields every Nth frame for processing — the rest are
    grabbed‑and‑discarded so the camera buffer stays fresh.
    This keeps latency < 100ms even on modest hardware.
    """

    def __init__(self):
        self.cap: cv2.VideoCapture | None = None
        self.frame_skip = config.FRAME_SKIP           # process every Nth frame
        self._frame_counter = 0
        self._last_yield_time = 0.0

    def open(self) -> None:
        """Open and configure the webcam."""
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        # Minimise internal buffer to reduce stale‑frame latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open webcam (index {config.CAMERA_INDEX}). "
                "Check CAMERA_INDEX in config.py"
            )
        print(f"[CAM] Camera opened (index={config.CAMERA_INDEX}, "
              f"skip={self.frame_skip})")

    def read(self):
        """
        Read the next frame.

        Returns:
            (should_process: bool, frame: ndarray | None)
            - should_process=True  → this is the frame to run YOLO on
            - should_process=False → frame was grabbed but skipped
            - frame=None           → camera error (retry)
        """
        if self.cap is None:
            raise RuntimeError("Camera not opened. Call open() first.")

        ret, frame = self.cap.read()
        if not ret:
            return False, None

        self._frame_counter += 1

        # Only process every Nth frame
        if self._frame_counter % self.frame_skip != 0:
            return False, frame          # skipped — still return frame for display

        self._last_yield_time = time.perf_counter()
        return True, frame               # process this one

    def release(self) -> None:
        """Release the webcam."""
        if self.cap:
            self.cap.release()
            print("[CAM] Camera released")

    @property
    def effective_fps(self) -> float:
        """Estimated effective processing FPS after skip."""
        raw_fps = self.cap.get(cv2.CAP_PROP_FPS) if self.cap else 30.0
        return raw_fps / self.frame_skip

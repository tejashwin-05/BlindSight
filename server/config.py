"""
EcoSight Server Configuration
"""
import os

# ─── Server ──────────────────────────────────────────────────────
WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8765

# ─── Camera ──────────────────────────────────────────────────────
CAMERA_INDEX = 0         # Try 1 if 0 fails
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# ─── Phase 1: Reflex Layer ───────────────────────────────────────
YOLO_MODEL = "yolov8n.pt"            # Nano model for speed
YOLO_CONFIDENCE_THRESHOLD = 0.50      # 50% — balance between precision and recall
PHASE1_TARGET_FPS = 10                # 10 FPS target
PHASE1_IMGSZ = 416                    # lower input size for faster inference
PHASE1_MAX_DETECTIONS = 20            # limit per-frame detections for stability
PHASE1_LOCK_SWITCH_CONFIRM_FRAMES = 2 # require consecutive misses before switching target

# Phase-1 architecture backends
# detector: yolo
# tracker: bytetrack | ocsort | simple
# depth: depth_anything_v2_small | heuristic
# free-space: heuristic (lane occupancy) | bisenetv2 | fast_scnn (future)
PHASE1_TRACKER_BACKEND = "bytetrack"
PHASE1_DEPTH_BACKEND = "heuristic"
PHASE1_FREE_SPACE_BACKEND = "heuristic"

# Depth Anything V2 (Small) model id (optional backend)
DEPTH_ANYTHING_MODEL_ID = "models/depth-anything-v2-small"
DEPTH_DISTANCE_SCALE = 2.5
DEPTH_MIN_VALUE = 1e-4

# Simple tracker fallback settings
TRACK_MAX_AGE_FRAMES = 8
TRACK_MATCH_MAX_CENTER_DELTA_PX = 120

# Path guidance tuning
GUIDANCE_LOWER_FRAME_START_RATIO = 0.45
GUIDANCE_MOVE_WORD = "slightly"

# Frame Skipping — process every Nth frame.
# Camera runs at ~30fps; skip=3 → ~10 processed frames/sec.
# Skipped frames are still grabbed to keep the buffer fresh.
FRAME_SKIP = 3

# Debounce / Anti‑Spam — prevents TTS from talking over itself
DEBOUNCE_COOLDOWN_SEC = 3.0           # seconds before re-alerting same hazard
DEBOUNCE_GLOBAL_MIN_SEC = 1.0         # minimum gap between ANY two alerts
DEBOUNCE_DISTANCE_CHANGE = 0.5        # re-alert if distance changes by >0.5m

# Hazard classes we care about (COCO class names + custom)
# COCO IDs: person=0, bicycle=1, car=2, ...
HAZARD_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    9: "traffic light",
    10: "fire hydrant",
    11: "stop sign", 
    13: "bench",
    15: "cat",
    16: "dog",
    24: "backpack",
    26: "handbag",
    28: "suitcase",
    39: "bottle",
    41: "cup",
    56: "chair",
    57: "couch",
    58: "potted plant",
    60: "dining table",
    63: "laptop",
    64: "mouse",
    66: "keyboard",
    67: "cell phone",
    73: "book",
}

# Monocular depth estimation calibration
# Focal_Constant = Known_Distance * Pixel_Height_at_Known_Distance
# Calibrated at 1 meter with a reference object ~200px tall
FOCAL_CONSTANT = 200.0

# Target tracking + hazard policy
# Always focus one nearest object at a time, flag as hazard when close,
# and switch to next object after user passes the current one.
NEAR_HAZARD_DISTANCE_M = 1.5
PASS_DISTANCE_INCREASE_M = 0.7
TARGET_LOST_FRAMES_TO_SWITCH = 4
TARGET_MATCH_CENTER_TOLERANCE_PX = 90

# Forward path filtering (used before alert selection)
# Object center-x must be inside [start, end] lane ratio, and bottom of box must
# be in lower part of frame (ground/near-path region).
PATH_ZONE_X_START = 0.25
PATH_ZONE_X_END = 0.75
PATH_ZONE_MIN_BOTTOM_Y_RATIO = 0.50

# Detection preprocessing (before single-target tracking)
DETECTION_MIN_DISTANCE_M = 0.3
DETECTION_MAX_DISTANCE_M = 8.0
DETECTION_MERGE_IOU_THRESHOLD = 0.45
DETECTION_MERGE_CENTER_DISTANCE_PX = 60

# Directionality zones (percentage of frame width)
LEFT_ZONE_END = 0.33
RIGHT_ZONE_START = 0.66

# ─── Phase 2: Context Layer ──────────────────────────────────────
# Keep False on CPU-heavy systems so Reflex loop stays smooth.
PHASE2_PRELOAD_ON_START = False
FLORENCE2_MODEL_ID = "models/florence-2-large"
FLORENCE2_TASKS = {
    "caption": "<DETAILED_CAPTION>",
    "vqa": "<VQA>",
    "ocr": "<OCR>",
    "od": "<OD>",
}

# ─── Connection Watchdog / Guardian Alert ─────────────────────────
# When the phone loses connection and can't reconnect within the
# watchdog windows, the server sends an SMS to the guardian.
WATCHDOG_RECONNECT_WINDOW_SEC = 15      # seconds to wait per retry window
WATCHDOG_MAX_RECONNECT_ATTEMPTS = 3     # failures before SMS fires

# Twilio credentials (set via env vars)
TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER   = os.getenv("TWILIO_FROM_NUMBER")

# Guardian / Emergency contact
GUARDIAN_PHONE_NUMBER = os.getenv("GUARDIAN_PHONE_NUMBER", "+918523072687")
USER_DISPLAY_NAME     = os.getenv("ECOSIGHT_USER_NAME", "EcoSight User")

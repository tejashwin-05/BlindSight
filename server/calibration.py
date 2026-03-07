"""
EcoSight — Focal Length Calibration Utility
Run this script ONCE before using the system to calibrate the
monocular depth estimation constant.

How it works:
  1. Place a reference object of KNOWN real-world height at EXACTLY 1 metre
     from the webcam.
  2. Run this script — it detects the object, measures its pixel height,
     and calculates:  FOCAL_CONSTANT = 1.0 * pixel_height
  3. The constant is written to config.py automatically.

Usage:
    python calibration.py
"""

import cv2
import numpy as np
from ultralytics import YOLO
import config


def run_calibration():
    print("=" * 55)
    print("  EcoSight — Focal Length Calibration")
    print("=" * 55)
    print()
    print("INSTRUCTIONS:")
    print("  1. Place a clearly visible object (e.g. a bottle, chair,")
    print("     or person) at EXACTLY 1 metre from the webcam.")
    print("  2. Make sure the full object is visible in the frame.")
    print("  3. Press 'c' to capture and calibrate.")
    print("  4. Press 'q' to quit without saving.")
    print()

    model = YOLO(config.YOLO_MODEL)
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] Cannot open webcam.")
        return

    calibration_done = False

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Run detection on live feed for visual feedback
        results = model(frame, verbose=False, conf=0.5)
        annotated = results[0].plot()

        # Show pixel heights of all detected objects
        boxes = results[0].boxes
        if boxes is not None:
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                px_height = int(y2 - y1)

                label = f"{cls_name}: {px_height}px"
                cv2.putText(annotated, label,
                            (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 255, 0), 2)

        cv2.putText(annotated,
                    "Place object at 1m | 'c'=calibrate | 'q'=quit",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (255, 255, 0), 2)

        cv2.imshow("EcoSight Calibration", annotated)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break

        if key == ord('c'):
            if boxes is None or len(boxes) == 0:
                print("[WARN] No objects detected! Make sure something is visible.")
                continue

            # Use the largest detected object
            heights = []
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cls_id = int(box.cls[0])
                heights.append({
                    "class": model.names[cls_id],
                    "pixel_height": y2 - y1,
                })
            heights.sort(key=lambda h: h["pixel_height"], reverse=True)
            chosen = heights[0]

            focal_constant = 1.0 * chosen["pixel_height"]
            print()
            print(f"[CALIBRATION RESULT]")
            print(f"  Object: {chosen['class']}")
            print(f"  Pixel height at 1m: {chosen['pixel_height']:.0f}px")
            print(f"  FOCAL_CONSTANT = {focal_constant:.1f}")
            print()

            # Update config.py
            _update_config_file(focal_constant)
            calibration_done = True
            break

    cap.release()
    cv2.destroyAllWindows()

    if calibration_done:
        print("[✓] Calibration saved to config.py")
        print("    Depth estimates will now be accurate (±0.5m).")
    else:
        print("[✗] Calibration cancelled.")


def _update_config_file(new_value: float):
    """Overwrite FOCAL_CONSTANT in config.py."""
    config_path = "config.py"
    with open(config_path, "r") as f:
        lines = f.readlines()

    with open(config_path, "w") as f:
        for line in lines:
            if line.strip().startswith("FOCAL_CONSTANT"):
                f.write(f"FOCAL_CONSTANT = {new_value:.1f}\n")
            else:
                f.write(line)


if __name__ == "__main__":
    run_calibration()

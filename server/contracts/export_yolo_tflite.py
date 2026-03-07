"""
Export helper: YOLOv8 .pt -> TFLite for mobile test version.

Usage (recommended from server venv):
  python contracts/export_yolo_tflite.py

Output copied to:
  ../client/assets/models/yolov8n.tflite
"""

from __future__ import annotations

from pathlib import Path

import torch
from ultralytics import YOLO


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    project_root = root.parent
    model_pt = root / "yolov8n.pt"
    client_model_dir = project_root / "client" / "assets" / "models"
    client_model_dir.mkdir(parents=True, exist_ok=True)

    if not model_pt.exists():
        raise FileNotFoundError(f"Missing model: {model_pt}")

    original_load = torch.load

    def patched_load(*args, **kwargs):
        if "weights_only" not in kwargs:
            kwargs["weights_only"] = False
        return original_load(*args, **kwargs)

    torch.load = patched_load

    model = YOLO(str(model_pt))

    export_attempts = [
        {
            "format": "tflite",
            "imgsz": 320,
            "half": False,
            "int8": False,
            "dynamic": False,
            "simplify": False,
            "nms": False,
            "opset": 18,
            "batch": 1,
        },
        {
            "format": "tflite",
            "imgsz": 640,
            "half": False,
            "int8": False,
            "dynamic": False,
            "simplify": False,
            "nms": False,
            "opset": 18,
            "batch": 1,
        },
    ]

    exported_path = None
    last_error: Exception | None = None
    for idx, attempt in enumerate(export_attempts, start=1):
        try:
            print(f"[export] Attempt {idx}/{len(export_attempts)} with args: {attempt}")
            exported_path = model.export(**attempt)
            break
        except Exception as exc:
            last_error = exc
            print(f"[export] Attempt {idx} failed: {exc}")

    if exported_path is None:
        raise RuntimeError(f"All export attempts failed. Last error: {last_error}")

    exported_file = Path(str(exported_path))
    if not exported_file.exists():
        raise FileNotFoundError(f"Export did not produce file: {exported_file}")

    target = client_model_dir / "yolov8n.tflite"
    target.write_bytes(exported_file.read_bytes())
    print(f"[export] Copied TFLite model -> {target}")


if __name__ == "__main__":
    main()

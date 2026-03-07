import os
import torch
import torch.serialization

# BYPASS 1: Force PyTorch 2.6 to accept YOLO classes
# This stops the "UnpicklingError" globally
torch.serialization.add_safe_globals([
    torch.nn.modules.container.Sequential,
    torch.nn.modules.conv.Conv2d,
    torch.nn.modules.batchnorm.BatchNorm2d,
    torch.nn.modules.activation.SiLU
])

# Monkeypatch torch.load to always use the "unsafe" mode required for YOLO
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load

from ultralytics import YOLO

# BYPASS 2: Force environment to use a stable TFLite path
# Setting this can help with specific TensorFlow version conflicts
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

def run_conversion():
    try:
        print("--- Loading YOLOv8n ---")
        # If yolov8n.pt isn't local, it will download a fresh, safe copy
        model = YOLO("yolov8n.pt") 

        print("--- Starting TFLite Export (Keras Path) ---")
        # 'keras=True' bypasses the onnx2tf "axes don't match" error
        # 'int8=False' keeps it as float32 for best compatibility in Flutter
        model.export(format="tflite", imgsz=640, keras=True, int8=False)
        
        print("\n✅ SUCCESS!")
        print("Check the 'yolov8n_saved_model' folder for your .tflite file.")
    except Exception as e:
        print(f"\n❌ EXPORT FAILED: {e}")

if __name__ == "__main__":
    run_conversion()

"""Convert an ONNX model to TFLite using onnx2tf (single-script wrapper).

Usage examples:
  python convert_onnx_to_tflite.py \
    --onnx server/yolov8n.onnx \
    --outdir server/onnx2tf_out \
    --autogen-replace                # run -agj to auto-generate replacement.json

  # INT8 quantize (uses onnx2tf -oiqt)
  python convert_onnx_to_tflite.py --onnx server/yolov8n.onnx --outdir out --quant int8 \
    --shape-hints "data:1,3,640,640" --batch-size 1

Notes:
- This script calls the `onnx2tf` CLI. Install it first (see README):
    pip install onnx2tf

- Defaults are conservative: float32 TFLite will be produced by onnx2tf
- To apply manual parameter replacement, pass `--replace path/to/replace.json`

"""
from __future__ import annotations
import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_onnx2tf_cmd() -> list[str]:
    """Return command list to invoke onnx2tf (prefers system script, falls back to -m)."""
    if shutil.which("onnx2tf"):
        return ["onnx2tf"]
    # fallback to `python -m onnx2tf` if package is installed but script not on PATH
    try:
        import onnx2tf  # type: ignore
        return [sys.executable, "-m", "onnx2tf"]
    except Exception:
        return []


def build_cmd(args: argparse.Namespace) -> list[str]:
    base = find_onnx2tf_cmd()
    if not base:
        raise RuntimeError(
            "onnx2tf not found. Install with: pip install onnx2tf (and TensorFlow)."
        )

    cmd = base + ["-i", str(Path(args.onnx).resolve())]

    # verbosity
    cmd += ["-v", args.verbosity]

    # replacement / auto-gen
    if args.autogen_replace:
        cmd.append("-agj")
    if args.replace:
        cmd += ["-prf", str(Path(args.replace).resolve())]

    # shapes / batch
    if args.batch_size is not None:
        cmd += ["-b", str(args.batch_size)]
    if args.shape_hints:
        cmd += ["-sh", args.shape_hints]
    if args.overwrite_input_shape:
        cmd += ["-ois", args.overwrite_input_shape]

    # transpose skip
    if args.skip_transpose:
        cmd += ["-kat", args.skip_transpose]

    # quant / precision choices
    if args.quant == "int8":
        cmd.append("-oiqt")
        if args.qt_mode:
            cmd += ["-qt", args.qt_mode]
    elif args.quant == "float16":
        cmd.append("-eatfp16")

    # pass-through extra options
    if args.extra:
        cmd += args.extra.split()

    return cmd


def run_conversion(cmd: list[str], outdir: Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"Running: {' '.join(cmd)}\n  (cwd={outdir})")
    proc = subprocess.run(cmd, cwd=outdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # write log
    log_path = outdir / "onnx2tf_conversion.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(proc.stdout or "")

    print(f"onnx2tf finished (rc={proc.returncode}). log: {log_path}\n")
    print(proc.stdout)
    return proc.returncode


def find_outputs(outdir: Path) -> dict[str, list[Path]]:
    out = {"tflite": [], "saved_model": [], "keras": [], "other": []}
    for p in outdir.glob("**/*"):
        if p.suffix == ".tflite":
            out["tflite"].append(p)
        elif p.name == "saved_model.pb" or p.is_dir() and p.name == "saved_model":
            out["saved_model"].append(p)
        elif p.suffix in (".h5", ".keras", ".json"):
            out["keras"].append(p)
        elif p.is_file():
            out["other"].append(p)
    return out


def simplify_onnx_model(input_path: Path) -> Path:
    """Try to simplify ONNX with onnx-simplifier; return path to simplified file or original if skipped/failed."""
    try:
        import onnx
        import onnxsim  # type: ignore
    except Exception:
        print("onnx-simplifier not available (pip install onnx-simplifier). Skipping simplification.")
        return input_path

    out_path = input_path.with_name(input_path.stem + ".simplified.onnx")
    print(f"Simplifying ONNX: {input_path} -> {out_path} ...")
    try:
        model_simp, check = onnxsim.simplify(str(input_path))
    except Exception as exc:  # pragma: no cover - runtime fallback
        print("onnx-simplifier failed:", exc)
        return input_path

    if not check:
        print("onnx-simplifier returned check==False; skipping simplified output")
        return input_path

    onnx.save(model_simp, str(out_path))
    print("Simplification succeeded.")
    return out_path


def quantize_saved_model_to_int8(saved_model_dir: Path, out_tflite_path: Path, rep_data_path: Path | None, rep_count: int = 1000) -> bool:
    """Use TensorFlow TFLiteConverter + representative dataset to produce int8 tflite.

    - rep_data_path may be a .npy file (N,H,W,C float32) or a directory of images.
    - Returns True on success.
    """
    try:
        import tensorflow as tf
        import numpy as np
    except Exception as ex:
        print("TensorFlow / numpy not available in the current environment:", ex)
        return False

    if not saved_model_dir.exists():
        print("SavedModel directory not found:", saved_model_dir)
        return False

    if rep_data_path is None or not rep_data_path.exists():
        print("Representative dataset not found; pass --representative-data path/to/data.npy or a folder of images.")
        return False

    def make_generator():
        if rep_data_path.suffix == ".npy":
            arr = np.load(rep_data_path)
            arr = arr.astype(np.float32)
            for i in range(min(len(arr), rep_count)):
                sample = arr[i]
                # ensure batch dim
                yield [np.expand_dims(sample, axis=0)]
        else:
            # directory of images
            from PIL import Image
            files = sorted([p for p in rep_data_path.iterdir() if p.suffix.lower() in ('.png', '.jpg', '.jpeg')])
            for i, p in enumerate(files[:rep_count]):
                img = Image.open(p).convert('RGB')
                arr = np.array(img).astype(np.float32)
                # add batch dim
                yield [np.expand_dims(arr, axis=0)]

    print(f"Quantizing SavedModel -> INT8 TFLite (output: {out_tflite_path}) using {rep_data_path}")
    converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model_dir))
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    # keep input/output as float32 for compatibility on many runtimes
    converter.inference_input_type = tf.float32
    converter.inference_output_type = tf.float32
    converter.representative_dataset = make_generator

    try:
        tflite_model = converter.convert()
    except Exception as ex:
        print("TFLiteConverter failed:", ex)
        return False

    out_tflite_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_tflite_path, 'wb') as f:
        f.write(tflite_model)

    print("Wrote quantized TFLite:", out_tflite_path)
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Convert ONNX -> TFLite using onnx2tf (wrapper)")
    p.add_argument("--onnx", required=True, help="Path to input ONNX file")
    p.add_argument("--outdir", default="onnx2tf_out", help="Output directory (created if needed)")
    p.add_argument("--replace", help="Path to replacement JSON (replace.json) to pass with -prf")
    p.add_argument("--autogen-replace", action="store_true", help="Run onnx2tf -agj to auto-generate replacement.json")
    p.add_argument("--shape-hints", help="Shape hints string for -sh (e.g. 'data:1,3,640,640')")
    p.add_argument("--batch-size", type=int, dest="batch_size", help="Set batch size with -b")
    p.add_argument("--overwrite-input-shape", dest="overwrite_input_shape", help="Use -ois to overwrite input shape")
    p.add_argument("--skip-transpose", dest="skip_transpose", help="Use -kat to suppress automatic transpose for named inputs")

    p.add_argument("--simplify", action="store_true", help="Run onnx-simplifier on the ONNX before conversion (requires onnx-simplifier)")
    p.add_argument("--representative-data", help="Path to .npy calibration data or folder of images for INT8 quantization")
    p.add_argument("--rep-count", type=int, default=1000, help="Max representative samples to use for TFLite quantization")
    p.add_argument("--use-tflite-quant", action="store_true", help="Use TensorFlow TFLiteConverter + representative dataset for INT8 quantization (post-conversion)")

    p.add_argument("--quant", choices=("float32", "float16", "int8"), default="float32", help="Output precision/quantization")
    p.add_argument("--qt-mode", choices=("per-channel", "per-tensor"), help="Quant mode passed to -qt when using int8 (onnx2tf)")
    p.add_argument("--verbosity", default="info", choices=("debug", "info", "warn", "error"), help="onnx2tf verbosity (-v)")
    p.add_argument("--extra", help="Extra raw onnx2tf CLI options to append")

    args = p.parse_args(argv)

    onnx_path = Path(args.onnx)
    if not onnx_path.exists():
        print(f"ERROR: ONNX file not found: {onnx_path}")
        return 2

    # optional simplification step
    if args.simplify:
        simplified = simplify_onnx_model(onnx_path)
        if simplified != onnx_path:
            onnx_path = simplified
            # mutate args so build_cmd picks the simplified path
            args.onnx = str(onnx_path)

    # set default representative-data if available in repo
    default_calib = Path("calibration_image_sample_data_20x128x128x3_float32.npy")
    if Path("server") / default_calib.name in Path("server").glob("*"):
        repo_default = Path("server") / default_calib.name
    else:
        repo_default = None

    if args.representative_data is None and repo_default and repo_default.exists():
        args.representative_data = str(repo_default)

    outdir = Path(args.outdir)

    # If user requested post-quantization via TFLiteConverter, avoid using onnx2tf's internal -oiqt
    if args.quant == 'int8' and args.use_tflite_quant:
        # ensure build_cmd won't append -oiqt
        args_for_build = argparse.Namespace(**vars(args))
        args_for_build.quant = 'float32'
    else:
        args_for_build = args

    try:
        cmd = build_cmd(args_for_build)
    except RuntimeError as ex:
        print(ex)
        print("Install onnx2tf (and TensorFlow) before running this script:")
        print("  pip install onnx2tf")
        return 3

    rc = run_conversion(cmd, outdir)
    outputs = find_outputs(outdir)

    if outputs["tflite"]:
        print("TFLite files produced:")
        for f in outputs["tflite"]:
            print("  -", f)
    else:
        print("No .tflite found in output directory. Check onnx2tf log above.")

    # If user asked for TF-Lite post-quantization using a representative dataset,
    # convert the SavedModel (generated by onnx2tf) with the TFLiteConverter.
    if args.quant == 'int8' and args.use_tflite_quant:
        # locate saved_model directory
        saved_model_dir = None
        for p in outputs.get('saved_model', []):
            if p.is_dir() and p.name == 'saved_model':
                saved_model_dir = p
                break
        if not saved_model_dir:
            # look for saved_model.pb parent
            for p in outputs.get('saved_model', []):
                if p.name == 'saved_model.pb':
                    saved_model_dir = p.parent
                    break

        if saved_model_dir:
            rep_path = Path(args.representative_data) if args.representative_data else None
            out_tflite_path = outdir / (onnx_path.stem + ".int8.tflite")
            ok = quantize_saved_model_to_int8(saved_model_dir, out_tflite_path, rep_path, args.rep_count)
            if ok:
                print("Post-quantization completed:", out_tflite_path)
            else:
                print("Post-quantization failed. See messages above for details.")
        else:
            print("SavedModel not found — cannot run TFLiteConverter quantization.")

    if rc != 0:
        print("Conversion failed: see log and adjust replace.json / shape hints / options.")
    else:
        print("Conversion appears to have completed — verify the TFLite model accuracy on sample inputs.")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())

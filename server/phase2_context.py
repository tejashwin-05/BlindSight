"""
EcoSight Phase 2 — Context Layer
On-demand scene description using Microsoft Florence-2 (local).
"""

import cv2
import torch
from PIL import Image
import numpy as np
from transformers import AutoProcessor, AutoModelForCausalLM
import config


class ContextLayer:
    """On‑demand deep scene understanding via Florence-2."""

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.model = None
        self.processor = None
        self._loaded = False
        self._load_error: str | None = None

    def load_model(self):
        """Lazily load Florence-2 (heavy model — only when needed)."""
        if self._loaded:
            return
        if self._load_error is not None:
            raise RuntimeError(self._load_error)
        print(f"[Phase2] Loading Florence-2 on {self.device}...")
        model_id = config.FLORENCE2_MODEL_ID

        try:
            # Default processor mode works with Florence local snapshot on pinned deps.
            self.processor = AutoProcessor.from_pretrained(
                model_id,
                trust_remote_code=True,
            )
        except Exception as e:
            print(f"[Phase2] Default processor load failed, trying slow tokenizer fallback: {e}")
            self.processor = AutoProcessor.from_pretrained(
                model_id,
                trust_remote_code=True,
                use_fast=False,
            )

        try:

            self.model = AutoModelForCausalLM.from_pretrained(
                model_id, trust_remote_code=True,
                torch_dtype=self.dtype,
            ).to(self.device)
            self.model.eval()
            self._loaded = True
            self._load_error = None
            print("[Phase2] Florence-2 loaded ✓")
        except Exception as e:
            self._load_error = f"Florence-2 load failed: {e}"
            print(f"[Phase2] {self._load_error}")
            raise

    def _run_task(self, image: Image.Image, task: str, text_input: str = "") -> str:
        """Run a Florence‑2 task and return decoded text."""
        self.load_model()

        prompt = task if not text_input else f"{task} {text_input}"
        inputs = self.processor(text=prompt, images=image, return_tensors="pt")
        inputs = {k: v.to(self.device, self.dtype) if v.dtype == torch.float32 else v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            generated_ids = self.model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=512,
                num_beams=3,
                early_stopping=True,
            )

        generated_text = self.processor.batch_decode(
            generated_ids, skip_special_tokens=False
        )[0]

        parsed = self.processor.post_process_generation(
            generated_text, task=task, image_size=(image.width, image.height)
        )

        # parsed is a dict keyed by task, value is the text string
        if isinstance(parsed, dict):
            return str(list(parsed.values())[0])
        return str(parsed)

    # ── Public API ─────────────────────────────────────────────
    def describe_scene(self, frame: np.ndarray) -> str:
        """Generate a detailed description of the current scene."""
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return self._run_task(image, config.FLORENCE2_TASKS["caption"])

    def answer_question(self, frame: np.ndarray, question: str) -> str:
        """Visual question answering on the current frame."""
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return self._run_task(image, config.FLORENCE2_TASKS["vqa"], question)

    def read_text(self, frame: np.ndarray) -> str:
        """OCR — read text visible in the frame."""
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return self._run_task(image, config.FLORENCE2_TASKS["ocr"])


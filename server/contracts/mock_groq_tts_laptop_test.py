"""
Mock test: Florence caption -> Groq rewrite -> Laptop TTS

Usage (PowerShell):
  $env:GROQ_API_KEY="your_key"
  python contracts/mock_groq_tts_laptop_test.py

Optional:
  python contracts/mock_groq_tts_laptop_test.py --caption "A person is near a doorway on the right"
  python contracts/mock_groq_tts_laptop_test.py --model "openai/gpt-oss-120b"
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request


GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "EcoSight-Mock-Groq-TTS/1.0",
    }


def check_groq_auth(api_key: str, timeout_sec: int = 15) -> None:
    req = urllib.request.Request(
        f"{GROQ_BASE_URL}/models",
        headers=_build_headers(api_key),
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        if resp.status < 200 or resp.status >= 300:
            raise RuntimeError(f"Groq auth check failed with status {resp.status}")


def call_groq(caption: str, model: str, timeout_sec: int = 20) -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Set it before running.")

    prompt = (
        "You are an accessibility assistant. Rewrite the caption into short spoken guidance.\n"
        "Rules: max 2 sentences, safety-first, do not invent details.\n"
        "Return ONLY JSON with key: spoken_text.\n\n"
        f"caption: {caption}\n"
    )

    body = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 180,
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": prompt},
        ],
    }

    req = urllib.request.Request(
        f"{GROQ_BASE_URL}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=_build_headers(api_key),
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8")

    parsed = json.loads(raw)
    content = (
        parsed.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    if not content:
        raise RuntimeError("Groq returned empty content")

    normalized = content
    if normalized.startswith("```"):
        normalized = normalized.strip("`")
        if normalized.startswith("json"):
            normalized = normalized[4:].strip()

    payload = json.loads(normalized)
    spoken = str(payload.get("spoken_text", "")).strip()
    if not spoken:
        raise RuntimeError("Groq JSON missing spoken_text")

    return spoken


def speak_text(text: str) -> None:
    try:
        import pyttsx3  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pyttsx3 not installed. Install with: pip install pyttsx3"
        ) from exc

    engine = pyttsx3.init()
    engine.setProperty("rate", 175)
    engine.setProperty("volume", 1.0)
    engine.say(text)
    engine.runAndWait()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--caption",
        default="A person is standing near a doorway slightly to your right.",
        help="Mock Florence caption text",
    )
    parser.add_argument(
        "--model",
        default="openai/gpt-oss-120b",
        help="Groq model id",
    )
    args = parser.parse_args()

    print("[mock-test] Input Florence caption:")
    print(args.caption)

    try:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is missing. In PowerShell: $env:GROQ_API_KEY='your_key'"
            )

        print("[mock-test] Checking Groq auth...")
        check_groq_auth(api_key)
        print("[mock-test] Groq auth check passed")

        spoken = call_groq(args.caption, args.model)
        print("\n[mock-test] Groq spoken output:")
        print(spoken)

        print("\n[mock-test] Speaking on laptop...")
        speak_text(spoken)
        print("[mock-test] Done")
        return 0
    except urllib.error.HTTPError as exc:
        print(f"[mock-test] Groq HTTP error: {exc.code}")
        try:
            details = exc.read().decode("utf-8")
            print(details)
            if exc.code == 403 and "1010" in details:
                print(
                    "[mock-test] 403/1010 indicates access denied by upstream policy. "
                    "Use a fresh valid Groq key and verify account/model access."
                )
        except Exception:
            pass
        return 2
    except Exception as exc:
        print(f"[mock-test] Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

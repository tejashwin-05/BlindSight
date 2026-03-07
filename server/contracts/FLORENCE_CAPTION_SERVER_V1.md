# Florence Caption Server v1

Standalone server for one-shot scene description (caption/ocr/vqa) from phone frame uploads.

## Why this server

Use this when you only want Florence scene description and do not want to run the full phase1 detection contract.

## Run

From `server/`:

```bash
python contracts/florence_caption_server_v1.py
```

Optional environment variables:

- `ECOSIGHT_FLORENCE_HOST` (default: `0.0.0.0`)
- `ECOSIGHT_FLORENCE_PORT` (default: `8090`)
- `ECOSIGHT_FLORENCE_API_KEY` (default: empty)
- `ECOSIGHT_FLORENCE_MAX_JPEG_BYTES` (default: `2097152`)
- `GROQ_API_KEY` (required for personalization)
- `ECOSIGHT_GROQ_ENABLED` (default: `1`)
- `ECOSIGHT_GROQ_MODEL` (default: `openai/gpt-oss-120b`)
- `ECOSIGHT_GROQ_TIMEOUT_SEC` (default: `12`)
- `ECOSIGHT_GROQ_MAX_TOKENS` (default: `220`)

## Endpoints

- `GET /health`
- `POST /v1/describe-scene`

### POST body

```json
{
  "frame_jpeg_base64": "...",
  "mode": "caption",
  "question": "What is on the table?",
  "personalize": {
    "enabled": true,
    "user_profile": {
      "language": "en-US",
      "verbosity": "concise",
      "mobility_mode": "pedestrian",
      "priority": "safety"
    },
    "context_hint": "User is walking and needs short actionable guidance."
  }
}
```

- `mode`: `caption` | `ocr` | `vqa`
- `question` required when `mode` is `vqa`
- `personalize.enabled=true` enables Groq rewrite with fallback to Florence raw text

### Success response

```json
{
  "ok": true,
  "mode": "caption",
  "text": "...",
  "source": "groq_augmented",
  "personalize_enabled": true,
  "reasoner_used": true,
  "reasoner_status": null,
  "latency_ms": 1200,
  "ts": 1739550000000
}

## Health readiness

`GET /health` also returns:

- `model_ready`, `model_loading`, `model_error`
- `personalization_available`
- `groq_model`
```

# Agentic Orchestrator Server v1

Standalone LangChain-based voice command orchestrator for day-to-day tasks.

Default LLM provider is local Ollama (`deepseek-r1:1.5b`).

## Run

From `server/`:

```bash
pip install -r contracts/requirements_agentic_v1.txt
ollama pull deepseek-r1:1.5b
python contracts/agentic_orchestrator_server_v1.py
```

Optional env vars:

- `ECOSIGHT_AGENT_HOST` (default `0.0.0.0`)
- `ECOSIGHT_AGENT_PORT` (default `8091`)
- `ECOSIGHT_AGENT_API_KEY` (optional)
- `ECOSIGHT_AGENT_MODEL` (default `deepseek-r1:1.5b`)
- `ECOSIGHT_OLLAMA_BASE_URL` (default `http://127.0.0.1:11434`)
- `ECOSIGHT_AGENT_TIMEOUT_SEC` (default `18`)

## Endpoint

- `GET /health`
- `POST /v1/agent/execute`

### Request

```json
{
  "text": "call mom",
  "context": {
    "latitude": 12.97,
    "longitude": 77.59
  }
}
```

### Response

```json
{
  "ok": true,
  "result": {
    "action": "call_relative",
    "speak_text": "Opening dialer to call mom.",
    "parameters": {
      "relative": "mom",
      "tel": "tel:+911111111111"
    }
  }
}
```

The client can execute `result.action` locally (`start_stream`, `stop_stream`, `describe_scene`, `call_relative`, etc.).

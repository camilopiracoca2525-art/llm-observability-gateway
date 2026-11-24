# LLM Observability Gateway

A standalone portfolio project demonstrating practical LLM engineering trade-offs: task-aware model routing, fallback, token accounting, latency, rate limiting, and estimated cost.

## Capabilities

- Routes `simple` tasks to an economy model profile and `complex` tasks to a quality model profile.
- Calls an OpenAI-compatible Chat Completions API.
- Falls back to the alternate configured model if the primary provider call fails.
- Includes mock mode so the project runs without API credentials.
- Limits requests per client using an in-memory sliding window.
- Tracks requests, failures, latency, token usage, estimated cost, and metrics by model.
- Uses configurable provider rates rather than assuming current prices.
- Includes automated tests and a GitHub Actions workflow.

## Architecture

```text
Client
  |
  v
FastAPI validation + rate limit
  |
  v
Task-aware Model Router
  |------------------|
  v                  v
Economy profile   Quality profile
  |                  |
  |---- fallback ----|
  |
  v
OpenAI-compatible API (or mock adapter)
  |
  v
Metrics Registry
  |
  v
JSON response + /api/metrics
```

## Requirements

- Python 3.10+
- API key optional; mock mode is the default.

## Run on Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn gateway.main:app --reload
```

Run the commands from the repository root. Open http://127.0.0.1:8000/docs.

## Run on macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn gateway.main:app --reload
```

## Try it in mock mode

The default `.env.example` uses `LLM_MODE=mock`, so there is no API key requirement and no paid model call.

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Summarize this request","task":"simple"}'
```

Change `task` to `complex` to select the quality profile.

## Connect a real provider

Edit `.env`:

```env
LLM_MODE=api
LLM_API_KEY=your_provider_key
LLM_BASE_URL=https://api.openai.com/v1
MODEL_ECONOMY=gpt-4o-mini
MODEL_QUALITY=gpt-4o
```

Both configured models must be available from your provider and support the OpenAI-compatible `/chat/completions` endpoint. Never commit a real API key.

Configure `MODEL_*_INPUT_COST_PER_1M` and `MODEL_*_OUTPUT_COST_PER_1M` using the provider's current prices per one million tokens. Defaults are zero so the application does not assume or rely on outdated pricing.

## API

- `GET /api/health` — mode and configured model profiles.
- `POST /api/chat` — submit a message and select `simple` or `complex`.
- `GET /api/metrics` — usage and latency aggregates, including per-model metrics.

Example request:

```json
{
  "message": "Classify this support ticket and suggest a next step.",
  "task": "simple"
}
```

Response fields include `selected_model`, `fallback_used`, `prompt_tokens`, `completion_tokens`, `estimated_cost`, and `end_to_end_latency_ms`.

## Tests

```bash
pytest -q
```

## Engineering trade-offs

| Area | Approach | Trade-off |
|---|---|---|
| Model selection | Two configurable profiles | Makes cost/quality choices explicit; task quality still needs evaluation |
| Fallback | Calls alternate profile after primary failure | Improves resilience but can add latency and cost |
| Rate limiting | In-memory sliding window per client | Simple for local demo; not distributed across workers |
| Token usage | Provider usage when available; estimate in mock mode | Mock estimates are approximate, not tokenizer output |
| Cost | Usage multiplied by configured rates | Accurate only when configured rates match current provider pricing |
| Metrics | In-memory aggregates | Resets on restart; production needs durable telemetry |

## Production hardening backlog

This is a learning/portfolio prototype, not a production gateway. Before production use, add authentication, shared rate limiting (Redis or equivalent), durable metrics, structured logs, request/response redaction, secret management, budget enforcement, evaluation datasets, load testing, and deployment configuration.

## Portfolio notes

Run the tests, try mock mode, configure a provider only if you have permission and an API budget, and be ready to explain the routing and fallback decisions in an interview.

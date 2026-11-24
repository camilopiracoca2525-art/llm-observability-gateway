import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from gateway.client import LLMClient
from gateway.limiter import RateLimitExceeded, SlidingWindowRateLimiter
from gateway.metrics import MetricsRegistry
from gateway.router import ModelProfile, ModelRouter

load_dotenv()


def env_float(name: str) -> float:
    try:
        return max(0.0, float(os.getenv(name, "0")))
    except ValueError:
        return 0.0


economy = ModelProfile(
    name=os.getenv("MODEL_ECONOMY", "gpt-4o-mini"),
    input_cost_per_1m=env_float("MODEL_ECONOMY_INPUT_COST_PER_1M"),
    output_cost_per_1m=env_float("MODEL_ECONOMY_OUTPUT_COST_PER_1M"),
)
quality = ModelProfile(
    name=os.getenv("MODEL_QUALITY", "gpt-4o"),
    input_cost_per_1m=env_float("MODEL_QUALITY_INPUT_COST_PER_1M"),
    output_cost_per_1m=env_float("MODEL_QUALITY_OUTPUT_COST_PER_1M"),
)

router = ModelRouter(economy, quality)
client = LLMClient(
    mode=os.getenv("LLM_MODE", "mock").lower(),
    api_key=os.getenv("LLM_API_KEY", ""),
    base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
)
limiter = SlidingWindowRateLimiter(
    int(os.getenv("RATE_LIMIT_REQUESTS", "15")),
    int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
)
metrics = MetricsRegistry()
max_message_chars = max(100, int(os.getenv("MAX_MESSAGE_CHARS", "6000")))

app = FastAPI(title="LLM Observability Gateway", version="1.0.0")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    task: str = Field(default="simple", pattern="^(simple|complex)$")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": client.mode,
        "profiles": {"economy": economy.name, "quality": quality.name},
    }


@app.get("/api/metrics")
def get_metrics():
    return metrics.snapshot()


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request):
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be blank.")
    if len(message) > max_message_chars:
        raise HTTPException(status_code=413, detail="Message is too long.")

    client_key = request.client.host if request.client else "unknown"
    try:
        limiter.check(client_key)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(limiter.window_seconds)},
        ) from exc

    primary = router.select(body.task)
    selected = primary
    fallback_used = False
    started = time.perf_counter()

    try:
        try:
            result = await client.complete(message, primary)
        except Exception:
            selected = router.fallback(primary)
            fallback_used = True
            result = await client.complete(message, selected)
    except Exception as exc:
        latency = (time.perf_counter() - started) * 1000
        metrics.record(selected.name, False, 0, 0, 0.0, latency)
        raise HTTPException(
            status_code=502,
            detail=f"All configured model attempts failed: {type(exc).__name__}",
        ) from exc

    latency = round((time.perf_counter() - started) * 1000, 2)
    metrics.record(
        selected.name,
        True,
        result["prompt_tokens"],
        result["completion_tokens"],
        result["estimated_cost"],
        latency,
    )
    return {
        **result,
        "requested_task": body.task,
        "selected_model": selected.name,
        "fallback_used": fallback_used,
        "end_to_end_latency_ms": latency,
    }

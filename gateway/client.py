import time
import httpx

from gateway.router import ModelProfile, estimate_cost, estimate_tokens


class LLMClient:
    def __init__(self, mode: str, api_key: str, base_url: str):
        self.mode = mode
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def complete(self, message: str, profile: ModelProfile):
        started = time.perf_counter()

        if self.mode != "api":
            answer = (
                f"[MOCK MODE - {profile.name}] Simulated response. "
                f"The prompt contains {len(message)} characters."
            )
            prompt_tokens = estimate_tokens(message)
            completion_tokens = estimate_tokens(answer)
            return {
                "answer": answer,
                "model": profile.name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "estimated_cost": estimate_cost(
                    prompt_tokens, completion_tokens, profile
                ),
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }

        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is not configured")

        payload = {
            "model": profile.name,
            "messages": [{"role": "user", "content": message}],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(40.0)) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            data = response.json()

        answer = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or estimate_tokens(message))
        completion_tokens = int(
            usage.get("completion_tokens") or estimate_tokens(answer)
        )
        return {
            "answer": answer,
            "model": data.get("model", profile.name),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost": estimate_cost(
                prompt_tokens, completion_tokens, profile
            ),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }

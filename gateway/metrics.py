import threading
from collections import defaultdict


class MetricsRegistry:
    """Thread-safe in-process metrics for a single demo instance."""

    def __init__(self):
        self._lock = threading.Lock()
        self._totals = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "estimated_cost": 0.0,
            "latency_total_ms": 0.0,
        }
        self._by_model = defaultdict(lambda: {
            "requests": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "estimated_cost": 0.0,
            "latency_total_ms": 0.0,
        })

    def record(
        self,
        model: str,
        success: bool,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        latency_ms: float,
    ):
        with self._lock:
            self._totals["requests"] += 1
            self._totals["successes" if success else "failures"] += 1
            self._totals["prompt_tokens"] += prompt_tokens
            self._totals["completion_tokens"] += completion_tokens
            self._totals["estimated_cost"] += cost
            self._totals["latency_total_ms"] += latency_ms

            item = self._by_model[model]
            item["requests"] += 1
            item["prompt_tokens"] += prompt_tokens
            item["completion_tokens"] += completion_tokens
            item["estimated_cost"] += cost
            item["latency_total_ms"] += latency_ms

    def snapshot(self):
        with self._lock:
            totals = dict(self._totals)
            count = totals["requests"]
            totals["average_latency_ms"] = (
                round(totals["latency_total_ms"] / count, 2) if count else 0.0
            )

            by_model = {}
            for name, values in self._by_model.items():
                copied = dict(values)
                copied["average_latency_ms"] = round(
                    copied["latency_total_ms"] / copied["requests"], 2
                )
                by_model[name] = copied

            return {"totals": totals, "by_model": by_model}

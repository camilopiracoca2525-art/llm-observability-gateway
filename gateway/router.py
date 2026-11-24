from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProfile:
    name: str
    input_cost_per_1m: float = 0.0
    output_cost_per_1m: float = 0.0


class ModelRouter:
    """Select a model profile using a task-complexity signal."""

    def __init__(self, economy: ModelProfile, quality: ModelProfile):
        self.economy = economy
        self.quality = quality

    def select(self, task: str) -> ModelProfile:
        normalized = task.strip().lower()
        if normalized == "simple":
            return self.economy
        if normalized == "complex":
            return self.quality
        raise ValueError("task must be 'simple' or 'complex'")

    def fallback(self, primary: ModelProfile) -> ModelProfile:
        return self.quality if primary == self.economy else self.economy


def estimate_tokens(text: str) -> int:
    """Rough mock estimate only; this is not a model tokenizer."""
    return max(1, (len(text) + 3) // 4) if text else 0


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    profile: ModelProfile,
) -> float:
    total = (
        max(0, prompt_tokens) * profile.input_cost_per_1m
        + max(0, completion_tokens) * profile.output_cost_per_1m
    ) / 1_000_000
    return round(total, 10)

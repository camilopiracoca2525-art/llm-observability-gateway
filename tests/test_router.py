import pytest

from gateway.limiter import RateLimitExceeded, SlidingWindowRateLimiter
from gateway.router import ModelProfile, ModelRouter, estimate_cost, estimate_tokens


def test_simple_and_complex_select_expected_profiles():
    economy = ModelProfile("economy-model", 0.1, 0.2)
    quality = ModelProfile("quality-model", 1.0, 2.0)
    router = ModelRouter(economy, quality)
    assert router.select("simple").name == "economy-model"
    assert router.select("complex").name == "quality-model"


def test_fallback_selects_alternate_profile():
    economy = ModelProfile("economy")
    quality = ModelProfile("quality")
    router = ModelRouter(economy, quality)
    assert router.fallback(economy).name == "quality"
    assert router.fallback(quality).name == "economy"


def test_invalid_task_is_rejected():
    router = ModelRouter(ModelProfile("economy"), ModelProfile("quality"))
    with pytest.raises(ValueError):
        router.select("unknown")


def test_token_estimate_and_cost_calculation():
    profile = ModelProfile("example", 1.0, 2.0)
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello") >= 1
    assert estimate_cost(1000, 500, profile) == pytest.approx(0.002)


def test_rate_limiter_blocks_over_limit():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    limiter.check("test-client")
    with pytest.raises(RateLimitExceeded):
        limiter.check("test-client")

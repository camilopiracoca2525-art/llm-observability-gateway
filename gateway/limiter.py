import time
from collections import defaultdict, deque


class RateLimitExceeded(Exception):
    """Raised when a client exceeds its configured request window."""


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max(1, max_requests)
        self.window_seconds = max(1, window_seconds)
        self.events = defaultdict(deque)

    def check(self, client_key: str):
        now = time.monotonic()
        queue = self.events[client_key]
        cutoff = now - self.window_seconds
        while queue and queue[0] <= cutoff:
            queue.popleft()
        if len(queue) >= self.max_requests:
            raise RateLimitExceeded("Request rate limit exceeded. Retry later.")
        queue.append(now)

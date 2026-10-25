"""Small per-client rate limiter for the registration endpoint."""

import asyncio
import math
import time
from collections import OrderedDict, deque
from collections.abc import Callable


class RateLimitExceeded(RuntimeError):
    """Raised when a client exceeds the configured attempt window."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Registration rate limit exceeded.")


class InMemoryRateLimiter:
    """Limit attempts per process while keeping no credential information."""

    def __init__(
        self,
        *,
        max_attempts: int,
        window_seconds: int,
        max_tracked_clients: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._max_tracked_clients = max_tracked_clients
        self._clock = clock
        self._attempts: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def check(self, client_key: str) -> None:
        """Record an allowed attempt or return a safe retry delay."""

        async with self._lock:
            now = self._clock()
            cutoff = now - self._window_seconds
            attempts = self._attempts.get(client_key)
            if attempts is None:
                if len(self._attempts) >= self._max_tracked_clients:
                    self._attempts.popitem(last=False)
                attempts = deque()
                self._attempts[client_key] = attempts
            else:
                self._attempts.move_to_end(client_key)

            while attempts and attempts[0] <= cutoff:
                attempts.popleft()

            if len(attempts) >= self._max_attempts:
                retry_after = math.ceil(self._window_seconds - (now - attempts[0]))
                raise RateLimitExceeded(max(1, retry_after))

            attempts.append(now)

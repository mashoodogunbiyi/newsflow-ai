"""Registration rate-limiter behaviour tests."""

import asyncio

import pytest

from app.security import InMemoryRateLimiter, RateLimitExceeded


def test_rate_limit_reports_retry_time_and_resets_after_window() -> None:
    current_time = [100.0]
    limiter = InMemoryRateLimiter(
        max_attempts=1,
        window_seconds=10,
        clock=lambda: current_time[0],
    )

    async def scenario() -> None:
        await limiter.check("client-one")
        with pytest.raises(RateLimitExceeded) as error:
            await limiter.check("client-one")

        assert error.value.retry_after_seconds == 10

        current_time[0] = 110.0
        await limiter.check("client-one")

    asyncio.run(scenario())


def test_rate_limit_bounds_the_number_of_tracked_clients() -> None:
    limiter = InMemoryRateLimiter(
        max_attempts=1,
        window_seconds=60,
        max_tracked_clients=2,
    )

    async def scenario() -> None:
        await limiter.check("client-one")
        await limiter.check("client-two")
        await limiter.check("client-three")

        await limiter.check("client-one")

    asyncio.run(scenario())

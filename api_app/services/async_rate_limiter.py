import asyncio


class AsyncRateLimiter:
    def __init__(self, interval_seconds: int):
        self._interval = interval_seconds
        self._last_call = None
        self._lock = asyncio.Lock()

    async def wait(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            if self._last_call is not None:
                elapsed = now - self._last_call
                if elapsed < self._interval:
                    await asyncio.sleep(self._interval - elapsed)
            self._last_call = asyncio.get_event_loop().time()

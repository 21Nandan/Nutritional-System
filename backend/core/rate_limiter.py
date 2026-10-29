"""
EATGOOD — In-Memory Rate Limiter & Abuse Protection
Provides thread-safe, sliding-window rate limiting for sensitive/expensive endpoints
(Open Food Facts searches and barcode lookups, and public user contributions).
State is per server instance, so on serverless hosts this is a best-effort limit, not a guarantee.
"""

import threading
import time

from fastapi import HTTPException, Request

from backend.config import (
    IS_SERVERLESS,
    RATE_LIMIT_CONTRIB_RPM,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_OFF_RPM,
    RATE_LIMIT_OFF_SEARCH_RPM,
)


class SlidingWindowRateLimiter:
    def __init__(self):
        self._history: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int = 60) -> tuple[bool, int]:
        """
        Evaluates whether a given key has exceeded max_requests in the window_seconds.
        Returns (is_limited: bool, retry_after_seconds: int).
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            timestamps = self._history.get(key, [])
            # Prune timestamps outside current sliding window
            valid_timestamps = [t for t in timestamps if t > window_start]

            if len(valid_timestamps) >= max_requests:
                oldest = valid_timestamps[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                self._history[key] = valid_timestamps
                return True, retry_after

            valid_timestamps.append(now)
            self._history[key] = valid_timestamps
            return False, 0

    def cleanup_stale_keys(self, max_idle_seconds: int = 300):
        """Periodically clears entries that have been idle for over 5 minutes."""
        now = time.time()
        with self._lock:
            keys_to_delete = [
                k for k, timestamps in self._history.items()
                if not timestamps or timestamps[-1] < (now - max_idle_seconds)
            ]
            for k in keys_to_delete:
                del self._history[k]

rate_limiter = SlidingWindowRateLimiter()

def get_client_identifier(request: Request) -> str:
    """Returns the client IP.

    On Vercel the edge overwrites X-Forwarded-For with the real client IP, so it can be
    trusted there. Anywhere else the header is client-controlled, so the socket peer is used.
    """
    if IS_SERVERLESS:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"

def enforce_rate_limit(request: Request, endpoint_type: str):
    """
    Dependency / helper to enforce rate limiting on specified endpoint types:
    'off_search', 'off_barcode', 'contribution'.
    """
    if not RATE_LIMIT_ENABLED:
        return

    limits = {
        "off_search": RATE_LIMIT_OFF_SEARCH_RPM,
        "off_barcode": RATE_LIMIT_OFF_RPM,
        "contribution": RATE_LIMIT_CONTRIB_RPM
    }
    max_reqs = limits.get(endpoint_type, 60)
    client_id = f"{endpoint_type}:{get_client_identifier(request)}"

    limited, retry_after = rate_limiter.is_rate_limited(client_id, max_requests=max_reqs, window_seconds=60)
    if limited:
        raise HTTPException(
            status_code=429,
            detail={
                "status": "rate_limited",
                "message": f"Rate limit exceeded for {endpoint_type}. Please retry in {retry_after} seconds.",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )

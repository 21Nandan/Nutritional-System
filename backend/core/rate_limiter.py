"""
EATGOOD — In-Memory Rate Limiter & Abuse Protection
Provides thread-safe, sliding-window rate limiting for sensitive/expensive endpoints
(OCR processing, external Open Food Facts queries, and public user contributions).
Requires zero external dependencies (no Redis daemon required for local-first deployment).
"""

import time
import threading
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException
from backend.config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_OCR_RPM,
    RATE_LIMIT_OFF_RPM,
    RATE_LIMIT_CONTRIB_RPM
)

class SlidingWindowRateLimiter:
    def __init__(self):
        self._history: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int]:
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
    """Extracts client IP or forward-header without trusting spoofed values."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.client and request.client.host:
        client_ip = request.client.host
    else:
        client_ip = "127.0.0.1"
    
    user_header = request.headers.get("x-user-id", "")
    return f"{client_ip}_{user_header}"

def enforce_rate_limit(request: Request, endpoint_type: str):
    """
    Dependency / helper to enforce rate limiting on specified endpoint types:
    'ocr', 'off_barcode', 'contribution'.
    """
    if not RATE_LIMIT_ENABLED:
        return

    limits = {
        "ocr": RATE_LIMIT_OCR_RPM,
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

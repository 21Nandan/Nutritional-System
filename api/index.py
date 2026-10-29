"""Vercel serverless entrypoint. Vercel serves the ASGI `app` defined here.

If the backend fails to import (missing data file, bad config), the exception propagates
and Vercel logs the full traceback; the function then returns 500 for every request.
"""

import sys
from pathlib import Path

# Vercel runs this file from api/; the backend package lives at the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.main import app  # noqa: E402

__all__ = ["app"]

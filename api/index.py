# EATGOOD Production Serverless Entrypoint — v1.2.0 (Dual-Engine Cloud Vision & Layer 1 UI)
import sys
import os

curr_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(curr_dir, ".."))

# Add repository root directories so 'backend' is strictly resolved from root
for p in [root_dir, os.getcwd(), "/var/task"]:
    if p and os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from backend.main import app

# Vercel looks for the ASGI/WSGI `app` object in this file

import sys
import os

# Add possible root directories to sys.path so 'backend' is always discoverable
curr_dir = os.path.dirname(os.path.abspath(__file__))
candidates = [
    curr_dir,
    os.path.abspath(os.path.join(curr_dir, "..")),
    os.path.abspath(os.path.join(curr_dir, "..", "..")),
    os.getcwd(),
    os.path.abspath(os.path.join(os.getcwd(), "backend")),
    os.path.abspath(os.path.join(os.getcwd(), "frontend")),
    "/var/task",
    "/var/task/frontend"
]
for p in candidates:
    if p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)

from backend.main import app

# Vercel looks for the ASGI/WSGI `app` object in this file

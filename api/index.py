import sys
import os

# Put project root directory in sys.path so 'backend' modules are found
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.main import app

# Vercel looks for the ASGI/WSGI `app` object in this file

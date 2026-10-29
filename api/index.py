# EATGOOD Production Serverless Entrypoint — v1.2.0 (Dual-Engine Cloud Vision & Layer 1 UI)
import sys
import os

curr_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(curr_dir, ".."))

# Add repository root directories so 'backend' is strictly resolved from root
for p in [root_dir, os.getcwd(), "/var/task"]:
    if p and os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    from backend.main import app
except Exception as e:
    import traceback
    tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI(title="EATGOOD Emergency Fallback")
    
    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def catch_all(path_name: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "serverless_init_error",
                "error": str(e),
                "traceback": tb.splitlines(),
                "cwd": os.getcwd(),
                "task_contents": os.listdir("/var/task") if os.path.exists("/var/task") else [],
                "sys_path": sys.path
            }
        )

# Vercel looks for the ASGI/WSGI `app` object in this file

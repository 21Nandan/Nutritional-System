"""
EATGOOD — FastAPI application.

Importing this module loads the catalogue and initialises the database. If either fails
the import raises, so a broken deployment fails loudly at startup instead of serving an
empty catalogue.
"""

import logging
import re
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import BASE_DIR, CORS_ORIGINS, IS_SERVERLESS
from backend.core.data_loader import data_loader
from backend.database import init_db
from backend.routes import catalogue, meta, scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("eatgood")

init_db()
logger.info(
    "Catalogue loaded: %d products, dataset %s (%s)",
    len(data_loader.products_df),
    data_loader.manifest["dataset_version"],
    data_loader.manifest["provenance"],
)

app = FastAPI(
    title="EATGOOD API",
    description="Nutrition grading, personal suitability and allergen checks for Indian packaged foods.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Eatgood-Profile", "X-Request-ID"],
)

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,64}$")


@app.middleware("http")
async def request_context(request: Request, call_next):
    incoming = request.headers.get("x-request-id", "")
    request_id = incoming if _REQUEST_ID_PATTERN.match(incoming) else uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    # Path only (no query string), so search terms and profile data never reach the logs.
    logger.info("request_id=%s method=%s path=%s status=%d duration_ms=%.1f",
                request_id, request.method, request.url.path, response.status_code, duration_ms)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
    return response


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("request_id=%s unhandled error on %s", request_id, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "error_code": "INTERNAL_ERROR",
                "message": "Something went wrong on our side. Please try again.",
                "request_id": request_id,
            }
        },
    )


app.include_router(meta.router)
app.include_router(scan.router)
app.include_router(catalogue.router)

# Local runs serve the built frontend from the same process. On Vercel the static
# files are served by the CDN and only /api/* reaches this app.
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
if not IS_SERVERLESS and (FRONTEND_DIST / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    # Only files that exist in the build at startup can be served; request paths are
    # looked up in this map and never joined onto the filesystem.
    STATIC_FILES = {
        path.relative_to(FRONTEND_DIST).as_posix(): path
        for path in FRONTEND_DIST.rglob("*")
        if path.is_file() and not path.relative_to(FRONTEND_DIST).as_posix().startswith("assets/")
    }
    INDEX_HTML = FRONTEND_DIST / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Unknown API route."})
        return FileResponse(STATIC_FILES.get(full_path, INDEX_HTML))

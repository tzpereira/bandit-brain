"""
Global request body size cap — a guardrail for a public deployment (see
ROADMAP.md Phase 4) independent of any per-route validation (e.g. ingest's
MAX_INGEST_BATCH_SIZE): rejects oversized requests before they're parsed.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

DEFAULT_MAX_BODY_BYTES = 2 * 1024 * 1024  # 2 MB


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes: int = DEFAULT_MAX_BODY_BYTES):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > self.max_body_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds the {self.max_body_bytes}-byte limit."},
            )
        return await call_next(request)

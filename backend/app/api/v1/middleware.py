"""FastAPI middleware for logging all HTTP requests to the audit log."""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.audit_log_service import AuditLogService


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every HTTP request to the SQLite audit log."""

    def __init__(self, app, audit_service: AuditLogService = None):
        super().__init__(app)
        self.audit = audit_service or AuditLogService()

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Process the request
        response: Response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log the request (skip health check and docs to reduce noise)
        path = request.url.path
        if path not in ("/health", "/", "/docs", "/redoc", "/openapi.json"):
            self.audit.log(
                level="error" if response.status_code >= 400 else "info",
                category="api",
                action="request",
                operator="user",
                endpoint=path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

        return response
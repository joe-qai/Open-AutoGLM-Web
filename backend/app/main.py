"""FastAPI main entry point for LOCKIN Agent Platform."""

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.v1 import tasks, devices, reports, websocket, scripts, apks, projects, settings as settings_router, logs, model_configs, control
from app.api.v1.middleware import AuditLogMiddleware
from app.core.agent.engine import AgentEngine
from app.config import settings
from app.db import db
from app.services.socketio_server import initialize_socketio


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle with graceful shutdown handling."""
    await db.init_db()
    app.state.agent_engine = AgentEngine()
    
    # Initialize Socket.IO server
    await initialize_socketio(app)
    
    try:
        yield
    except asyncio.CancelledError:
        # Gracefully handle server shutdown (Ctrl+C or kill signal)
        pass
    finally:
        try:
            await db.close()
        except Exception:
            # Ignore errors during shutdown
            pass


app = FastAPI(
    title="LOCKIN Agent Platform",
    description="Multi-platform Mobile Agent Testing Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — handles preflight correctly
# Socket.IO has its own CORS handling for /socket.io/* paths
from starlette.middleware.base import BaseHTTPMiddleware

class APICORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS":
            origin = request.headers.get("origin", "")
            allowed = ["http://localhost:3000", "http://localhost:3001",
                       "http://127.0.0.1:3000", "http://127.0.0.1:3001", "null"]
            if origin in allowed:
                from starlette.responses import Response
                resp = Response()
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Credentials"] = "true"
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
                return resp
        if request.url.path.startswith("/socket.io"):
            return await call_next(request)
        
        response = await call_next(request)
        origin = request.headers.get("origin")
        allowed_origins = ["http://localhost:3000", "http://localhost:3001",
                           "http://127.0.0.1:3000", "http://127.0.0.1:3001", "null"]
        if origin and origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

app.add_middleware(APICORSMiddleware)

# Audit log middleware — logs all API requests to SQLite
app.add_middleware(AuditLogMiddleware)

# Include API routers
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(scripts.router, prefix="/api/v1/scripts", tags=["scripts"])
app.include_router(apks.router, prefix="/api/v1/apks", tags=["apks"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(model_configs.router, prefix="/api/v1/model_configs", tags=["model_configs"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
app.include_router(control.router, prefix="/api/v1/control", tags=["control"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "message": "LOCKIN Agent Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/socket.io/test")
async def test_socketio():
    """Test Socket.IO connection."""
    return {"status": "Socket.IO server is running"}

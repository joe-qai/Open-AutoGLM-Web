"""FastAPI main entry point for LOCKIN Agent Platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.v1 import tasks, devices, reports, websocket, scripts, apks, projects, settings as settings_router, logs, model_configs
from app.api.v1.middleware import AuditLogMiddleware
from app.core.agent.engine import AgentEngine
from app.config import settings
from app.db import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    await db.init_db()
    app.state.agent_engine = AgentEngine()
    yield
    await db.close()


app = FastAPI(
    title="LOCKIN Agent Platform",
    description="Multi-platform Mobile Agent Testing Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

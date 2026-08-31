"""
VitalNode Backend - FastAPI Application Entry Point

Registers all routers, configures CORS, global error handlers, and startup events.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.exceptions import (
    VitalNodeError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    InvalidVitalError,
    ConflictError,
    MLUnavailableError,
    DemoModeError,
)
from app.db.database import engine

# Import all models so Alembic can detect them
from app.models import user, patient, encounter, assessment, vital  # noqa: F401
from app.models import recommendation, audit, notification, device, queue_entry  # noqa: F401

# Import routers
from app.api.v1 import auth, patients, assessments, queue, reassessments
from app.api.v1 import notifications, audit as audit_router, surge
from app.api.v1 import devices, voice, system as system_router, demo
from app.api.v1 import websocket as ws_router
from app.api.v1 import history_lookup

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info(
        "vitalnode_starting",
        env=settings.app_env,
        version=settings.app_version,
        ml_engine=settings.ml_engine,
        demo_mode=settings.demo_mode,
    )
    # Start background reassessment worker (fires every 60 seconds)
    from app.workers.reassessment_worker import run_loop
    asyncio.create_task(run_loop(interval_seconds=60))
    logger.info("reassessment_worker_scheduled", interval_seconds=60)

    # Pre-load ML engine at startup so first request isn't slow
    from app.services.assessment_service import _get_ml_engine, reset_ml_engine
    reset_ml_engine()  # Clear any cached instance from previous reload
    engine = _get_ml_engine()
    logger.info("ml_engine_loaded", engine=engine.get_version(), available=engine.is_available(), type=type(engine).__name__)

    yield
    logger.info("vitalnode_shutdown")
    await engine.dispose()


# ── App factory ────────────────────────────────────────────────────────────

app = FastAPI(
    title="VitalNode API",
    description=(
        "VitalNode AI-assisted emergency triage backend. "
        "Prototype for Accenture Innovation Challenge 2026. "
        "NOT clinically validated. NOT for actual patient care."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global error handlers ──────────────────────────────────────────────────

def _error_response(code: str, message: str, details: dict = None, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return _error_response(exc.code, exc.message, exc.details, status.HTTP_401_UNAUTHORIZED)


@app.exception_handler(AuthorizationError)
async def authz_error_handler(request: Request, exc: AuthorizationError):
    return _error_response(exc.code, exc.message, exc.details, status.HTTP_403_FORBIDDEN)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return _error_response(exc.code, exc.message, exc.details, status.HTTP_404_NOT_FOUND)


@app.exception_handler(InvalidVitalError)
async def invalid_vital_handler(request: Request, exc: InvalidVitalError):
    return _error_response(exc.code, exc.message, exc.details, status.HTTP_422_UNPROCESSABLE_ENTITY)


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return _error_response(exc.code, exc.message, exc.details, status.HTTP_422_UNPROCESSABLE_ENTITY)


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return _error_response(exc.code, exc.message, exc.details, status.HTTP_409_CONFLICT)


@app.exception_handler(MLUnavailableError)
async def ml_unavailable_handler(request: Request, exc: MLUnavailableError):
    return _error_response(exc.code, exc.message, exc.details, status.HTTP_503_SERVICE_UNAVAILABLE)


@app.exception_handler(DemoModeError)
async def demo_mode_handler(request: Request, exc: DemoModeError):
    return _error_response(exc.code, exc.message, exc.details, status.HTTP_403_FORBIDDEN)


@app.exception_handler(VitalNodeError)
async def generic_app_error_handler(request: Request, exc: VitalNodeError):
    return _error_response(exc.code, exc.message, exc.details, status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    # Log full traceback server-side, never expose it to the client
    logger.exception("unhandled_error", path=str(request.url), error=str(exc))
    return _error_response(
        "INTERNAL_ERROR",
        "An unexpected error occurred. Please try again.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ── Health check (unauthenticated) ─────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="API health check")
async def health():
    """Returns current status of API and connected services."""
    from sqlalchemy import text
    from app.db.database import AsyncSessionLocal

    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    ml_status = settings.ml_engine
    voice_status = settings.speech_provider

    overall = "ok" if db_status == "ok" else "degraded"

    return {
        "status": overall,
        "api": "ok",
        "database": db_status,
        "ml": ml_status,
        "voice": voice_status,
        "version": settings.app_version,
        "environment": settings.app_env,
        "demo_mode": settings.demo_mode,
    }


# ── Register all routers ───────────────────────────────────────────────────

PREFIX = "/api/v1"

app.include_router(auth.router,           prefix=PREFIX)
app.include_router(patients.router,       prefix=PREFIX)
app.include_router(assessments.router,    prefix=PREFIX)
app.include_router(queue.router,          prefix=PREFIX)
app.include_router(reassessments.router,  prefix=PREFIX)
app.include_router(notifications.router,  prefix=PREFIX)
app.include_router(audit_router.router,   prefix=PREFIX)
app.include_router(surge.router,          prefix=PREFIX)
app.include_router(devices.router,        prefix=PREFIX)
app.include_router(voice.router,          prefix=PREFIX)
app.include_router(system_router.router,  prefix=PREFIX)
app.include_router(ws_router.router,       prefix=PREFIX)
app.include_router(history_lookup.router,  prefix=PREFIX)

# Demo endpoints only available when DEMO_MODE=true
if settings.demo_mode:
    app.include_router(demo.router, prefix=PREFIX)
    logger.info("demo_endpoints_enabled")

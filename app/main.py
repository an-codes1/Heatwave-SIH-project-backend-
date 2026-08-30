from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any

import sqlalchemy as sa
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger, log_event
from app.core.security import SecurityHeadersMiddleware
from app.db.session import get_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    log_event(logger, "INFO", "application startup", app=settings.app_name)

    try:
        async for session in get_db():
            await session.execute(sa.text("SELECT 1"))
        log_event(logger, "INFO", "database connectivity ok")
    except Exception:
        log_event(logger, "WARNING", "database connectivity failed at startup")

    yield

    log_event(logger, "INFO", "application shutdown")


OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Liveness and database readiness probes.",
    },
    {
        "name": "Stations",
        "description": "Operational weather stations in Bhubaneswar.",
    },
    {
        "name": "Zones",
        "description": "The 67 municipal wards of Bhubaneswar.",
    },
    {
        "name": "Thermal",
        "description": "Human thermal comfort indices (MRT, UTCI, heat risk "
        "score) for each ward, for both observed history and forecast.",
    },
    {
        "name": "Forecast",
        "description": "Five-day open-meteo weather forecast fields.",
    },
    {
        "name": "Risk",
        "description": "Ward-level heat-health risk as GeoJSON and "
        "tabular summaries.",
    },
    {
        "name": "Alerts",
        "description": "Heat alert generation and WhatsApp/SMS "
        "notification dispatch (dry-run by default).",
    },
]

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend for SIH Problem Statement 83 - Extreme Heatwave "
        "Early Warning and Human Thermal Stress Index. Computes "
        "ward-level heat-health risk for all 67 Bhubaneswar wards "
        "from ERA5 history and a five-day Open-Meteo forecast."
    ),
    version="0.2.0",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    _: Request, exc: Exception
) -> JSONResponse:
    log_event(logger, "ERROR", "unhandled exception", error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."},
    )


@app.get(
    "/health",
    tags=["Health"],
    summary="Liveness probe",
    description="Lightweight check that the API process is running.",
)
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get(
    "/health/db",
    tags=["Health"],
    summary="Database readiness probe",
    description="Executes SELECT 1 against PostgreSQL and reports latency.",
)
async def health_db() -> dict[str, Any]:
    started = perf_counter()
    try:
        async for session in get_db():
            result = await session.execute(sa.text("SELECT 1"))
            value = result.scalar()
        latency_ms = round((perf_counter() - started) * 1000, 2)
    except Exception:
        log_event(logger, "WARNING", "database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        )

    return {
        "status": "healthy",
        "database": "ok",
        "test": value,
        "latency_ms": latency_ms,
    }
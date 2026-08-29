from typing import Any

import sqlalchemy as sa
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.db.session import get_db

app = FastAPI(
    title=settings.app_name,
    description="Backend for SIH Problem Statement 83 - "
    "Extreme Heatwave Early Warning and Human Thermal Stress Index",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict[str, Any]:
    try:
        async for session in get_db():
            result = await session.execute(sa.text("SELECT 1"))
            value = result.scalar()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        )

    return {"status": "ok", "database": "ok", "test": value}
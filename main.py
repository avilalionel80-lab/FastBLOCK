import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.endpoints.asistencia import comite_client, router as asistencia_router

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await comite_client.aclose()


app = FastAPI(
    title="NetShield Security Bridge API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(asistencia_router, prefix="/api/v1")

if os.getenv("MOCK_MODE", "true").lower() in ("1", "true", "yes"):
    from app.api.v1.endpoints.mock import router as mock_router
    app.include_router(mock_router, prefix="/mock")

import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from app.config import get_settings
from app.database import init_db
from app.routers import auth, data, ledger, asistencia, captive, admin
from app.middleware.rate_limit import RateLimitMiddleware


class ClaveInvalida(Exception):
    pass


class NodoCaido(Exception):
    pass


class FirmaInvalida(Exception):
    pass


EXCEPTION_MAP = {
    ClaveInvalida: (400, "CLAVE_INVALIDA"),
    NodoCaido: (503, "NODO_CAIDO"),
    FirmaInvalida: (401, "FIRMA_INVALIDA"),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.remove()
    settings = get_settings()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    logger.info("NetShield API starting...")
    init_db()
    if settings.mock_blockchain:
        logger.info("Running in SIMULATION mode (MOCK_BLOCKCHAIN=true)")
    else:
        logger.info("Running in PRODUCTION mode")
    yield
    logger.info("NetShield API shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="NetShield REST API",
        description="API puente entre la aplicación web y el comité blockchain Hyperledger Besu",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    app.add_middleware(RateLimitMiddleware)

    app.include_router(auth.router)
    app.include_router(data.router)
    app.include_router(ledger.router)
    app.include_router(asistencia.router)
    app.include_router(captive.router)
    app.include_router(admin.router)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        for exc_type, (status, code) in EXCEPTION_MAP.items():
            if isinstance(exc, exc_type):
                logger.error(f"{code}: {exc}")
                return JSONResponse(
                    status_code=status,
                    content={"detail": str(exc), "error_code": code},
                )
        logger.opt(exception=True).error(f"Unhandled error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
        )

    @app.get("/")
    async def root():
        return {
            "app": "NetShield API",
            "version": "1.0.0",
            "docs": "/docs" if settings.debug else "not available",
        }

    return app


app = create_app()

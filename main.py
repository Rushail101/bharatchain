"""
main.py — BharatChain Entry Point
==================================
This is the file you run to start the entire system.
It does 4 things in order:
    1. Creates the FastAPI app
    2. Connects the database
    3. Connects to the blockchain backend
    4. Registers all API route modules

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Or simply:
    python main.py
"""

import logging
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from config import settings

# ── Database ──────────────────────────────────────────────────────────────────
from db.session import init_db

# ── Core systems ──────────────────────────────────────────────────────────────
from core.blockchain import blockchain          # the chain connection object
from core.crypto import crypto_engine          # encryption / hashing engine

# ── API Routers (one per module) ──────────────────────────────────────────────
# We will build each of these files next, one by one.
# Each router handles a group of related API endpoints.
from api.routes_identity import router as identity_router
from api.routes_health import router as health_router
from api.routes_financial import router as financial_router
from api.routes_property import router as property_router
from api.routes_assets import router as assets_router
from api.routes_consent import router as consent_router


# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),                          # print to terminal
        logging.FileHandler(settings.LOG_FILE),           # also save to file
    ],
)
logger = logging.getLogger("bharatchain.main")


# ── Lifespan: runs on startup and shutdown ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Everything BEFORE yield → runs on startup.
    Everything AFTER yield  → runs on shutdown.
    This replaces the old @app.on_event("startup") pattern.
    """

    # ── STARTUP ──────────────────────────────────────────────────────────
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # 1. Initialize database — creates tables if they don't exist yet
    logger.info("Connecting to database...")
    await init_db()
    logger.info("✓ Database ready")

    # 2. Connect to blockchain backend
    logger.info(f"Connecting to blockchain ({settings.BLOCKCHAIN_BACKEND})...")
    await blockchain.connect()
    logger.info(f"✓ Blockchain connected — backend: {settings.BLOCKCHAIN_BACKEND}")

    # 3. Initialize encryption engine
    logger.info("Initializing crypto engine...")
    crypto_engine.initialize()
    logger.info("✓ Crypto engine ready")

    logger.info("=" * 50)
    logger.info(f"  {settings.APP_NAME} is LIVE on port {settings.PORT}")
    logger.info("=" * 50)

    yield   # ← App runs here (handles all requests)

    # ── SHUTDOWN ──────────────────────────────────────────────────────────
    logger.info("Shutting down — closing connections...")
    await blockchain.disconnect()
    logger.info("✓ Shutdown complete")


# ── Create the FastAPI app ────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Universal Digital Identity & Asset Registry on Blockchain",
    docs_url="/docs",          # Swagger UI at http://localhost:8000/docs
    redoc_url="/redoc",        # ReDoc UI at http://localhost:8000/redoc
    lifespan=lifespan,
)


# ── Middleware ─────────────────────────────────────────────────────────────────
# CORS — allows your frontend (HTML dashboard) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security — only accept requests from known hosts in production
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["bharatchain.gov.in", "*.bharatchain.gov.in"],
    )


# ── Register all routers ──────────────────────────────────────────────────────
# Each router is a group of related endpoints defined in api/routes_*.py
# The prefix means: /identity/..., /health/..., etc.
# The tags group them in the Swagger docs.

app.include_router(identity_router,  prefix="/identity",  tags=["Identity"])
app.include_router(health_router,    prefix="/health",    tags=["Health Records"])
app.include_router(financial_router, prefix="/financial", tags=["Financial ID"])
app.include_router(property_router,  prefix="/property",  tags=["Property Registry"])
app.include_router(assets_router,    prefix="/assets",    tags=["Capital Assets"])
app.include_router(consent_router,   prefix="/consent",   tags=["Consent Engine"])


# ── Root endpoint ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Status"])
async def root():
    """Health check — confirms the API is running."""
    return {
        "system": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "blockchain": settings.BLOCKCHAIN_BACKEND,
        "docs": "/docs",
    }


@app.get("/health-check", tags=["Status"])
async def health_check():
    """Deep health check — confirms DB and blockchain are connected."""
    return {
        "api": "ok",
        "database": "ok",
        "blockchain": await blockchain.ping(),
        "crypto": crypto_engine.is_ready(),
    }


# ── Run directly ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,    # auto-reload on file changes in dev mode
        log_level=settings.LOG_LEVEL.lower(),
    )

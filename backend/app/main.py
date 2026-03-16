"""
DevRel-in-a-Box — FastAPI Application
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import intent, workspace, debug, analytics, ingest, health
from app.db.session import init_db
from app.services.vector_store import VectorStore
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Initialise database tables
    await init_db()
    # Warm up vector store connection
    vs = VectorStore()
    await vs.connect()
    app.state.vector_store = vs
    print("✅ DevRel-in-a-Box ready")
    yield
    # Cleanup
    await vs.close()


app = FastAPI(
    title="DevRel-in-a-Box API",
    description="AI-powered Developer Relations platform",
    version="0.1.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────
app.include_router(health.router,     prefix="/health",    tags=["health"])
app.include_router(intent.router,     prefix="/api/intent",    tags=["intent"])
app.include_router(workspace.router,  prefix="/api/workspace", tags=["workspace"])
app.include_router(debug.router,      prefix="/api/debug",     tags=["debug"])
app.include_router(analytics.router,  prefix="/api/analytics", tags=["analytics"])
app.include_router(ingest.router,     prefix="/api/ingest",    tags=["ingest"])

# ─── Static files (widget + dashboard) ───────────────────
app.mount("/", StaticFiles(directory=str(Path(__file__).resolve().parents[2] / "frontend"), html=True), name="frontend")

"""
main.py – DevRelOS FastAPI Application
AI DevRel-in-a-Box: autonomous Developer Relations platform
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Add project root to path so sub-packages resolve correctly
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db
from routes.chat       import router as chat_router
from routes.execute    import router as execute_router
from routes.api_routes import router as api_router


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle manager."""
    print("╔══════════════════════════════════════════╗")
    print("║          DevRelOS  –  Starting up        ║")
    print("╚══════════════════════════════════════════╝")
    await init_db()
    yield
    print("[DevRelOS] Shutting down …")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "DevRelOS – AI DevRel-in-a-Box",
    description = "Autonomous AI-powered Developer Relations platform",
    version     = "1.0.0",
    lifespan    = lifespan,
    docs_url    = "/swagger",
    redoc_url   = "/redoc",
)

# CORS
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins     = origins,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code = 500,
        content     = {"error": str(exc), "path": str(request.url)},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(chat_router)
app.include_router(execute_router)
app.include_router(api_router)


# ── Static files ──────────────────────────────────────────────────────────────

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ── HTML Routes ───────────────────────────────────────────────────────────────

templates_dir = os.path.join(os.path.dirname(__file__), "templates")

@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(os.path.join(templates_dir, "index.html"))

@app.get("/analytics", include_in_schema=False)
async def analytics_page():
    return FileResponse(os.path.join(templates_dir, "analytics.html"))

@app.get("/docs-ui", include_in_schema=False)
async def docs_page():
    return FileResponse(os.path.join(templates_dir, "docs.html"))


# ── Dev entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host    = os.getenv("HOST", "0.0.0.0"),
        port    = int(os.getenv("PORT", 8000)),
        reload  = os.getenv("DEBUG", "true").lower() == "true",
        log_level = "info",
    )

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from ..storage.logging_config import setup_logging
from ..storage.db_init import init_database

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "memory_system.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Intelligent Memory System API")
    init_database(str(DB_PATH))
    logger.info(f"Database initialized at {DB_PATH}")
    yield
    logger.info("Shutting down Intelligent Memory System API")


app = FastAPI(
    title="Intelligent Memory System API",
    description="REST API for intelligent memory management with automatic organization",
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

from .routers import memory, query, config, report, dashboard

app.include_router(memory.router, prefix="/api/v1/memories", tags=["memories"])
app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
app.include_router(config.router, prefix="/api/v1/configs", tags=["configs"])
app.include_router(report.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "src" / "api" / "static")),
    name="static",
)


@app.get("/")
async def root():
    return {
        "message": "Intelligent Memory System API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

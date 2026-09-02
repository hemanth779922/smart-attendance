import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.session import init_db
from app.api.api_v1.router import api_router
from app.ai.face_engine import load_cascades

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smart_attendance")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan:
    - Initialize database tables and seed default users
    - Pre-load AI and Computer Vision models once into memory (Optimization requirement #13)
    """
    logger.info("Initializing Smart Attendance System 2.0...")
    
    # 1. Database init
    init_db()
    
    # 2. AI Model singleton warmup
    load_cascades()
    logger.info("AI/CV processing engine warmed up and ready.")
    
    yield
    
    logger.info("Shutting down Smart Attendance System.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Upgraded AI-Powered Face Recognition Smart Attendance System with Low-Light Enhancement, Multi-Signal Anti-Spoofing, and pgvector.",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Timing middleware to measure API response time and add X-Process-Time header."""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    return response


# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

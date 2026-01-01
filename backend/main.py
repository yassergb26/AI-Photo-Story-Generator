"""
FastAPI Main Application
Milestone 1: Foundation & Core Infrastructure
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from pathlib import Path

from app.config import settings
from app.database import engine, Base
from app.routers import photos, classifications, patterns, stories, emotions, narratives, life_events, exports, chapters, tasks

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Configure rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload and thumbnail directories
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path("./thumbnails").mkdir(parents=True, exist_ok=True)

# Mount static files for uploaded images and thumbnails
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/thumbnails", StaticFiles(directory="./thumbnails"), name="thumbnails")

# Include routers
app.include_router(photos.router)  # New photos API
app.include_router(classifications.router)
app.include_router(patterns.router)
app.include_router(stories.router)
app.include_router(emotions.router)  # Milestone 5: Emotion Detection
app.include_router(narratives.router)  # Milestone 5: AI Narratives
app.include_router(life_events.router)  # Milestone 6: Life Events System
app.include_router(exports.router)  # Milestone 6: Export Features
app.include_router(chapters.router)  # NEW: Chapters & Story Arcs System
app.include_router(tasks.router)  # Task status endpoints for async operations


@app.get("/")
def read_root():
    """Health check endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "upload_dir": settings.UPLOAD_DIR
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )

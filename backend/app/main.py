from fastapi import FastAPI

from app.api.content_profiles import router as content_profiles_router
from app.api.health import router as health_router
from app.api.ideas import router as ideas_router
from app.api.videos import router as videos_router

app = FastAPI(title="AI Video Factory")
app.include_router(health_router, prefix="/api/v1")
app.include_router(content_profiles_router, prefix="/api/v1")
app.include_router(ideas_router, prefix="/api/v1")
app.include_router(videos_router, prefix="/api/v1")

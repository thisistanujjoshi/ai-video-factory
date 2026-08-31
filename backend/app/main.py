from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.content_profiles import router as content_profiles_router
from app.api.health import router as health_router
from app.api.ideas import router as ideas_router
from app.api.videos import router as videos_router

app = FastAPI(title="AI Video Factory")

# ponytail: wide-open CORS for the dev dashboard (default Next.js port).
# Fine for local dev; tighten to a configured origin list before any real
# deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(content_profiles_router, prefix="/api/v1")
app.include_router(ideas_router, prefix="/api/v1")
app.include_router(videos_router, prefix="/api/v1")

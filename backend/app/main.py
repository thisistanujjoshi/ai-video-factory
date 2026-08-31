from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(title="AI Video Factory")
app.include_router(health_router, prefix="/api/v1")

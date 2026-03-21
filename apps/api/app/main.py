from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.modules.analysis_results.router import router as analysis_results_router
from app.modules.compare.router import router as compare_router
from app.modules.tasks.router import router as tasks_router
from app.routers import health
from app.routers.translate import router as translate_router

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(translate_router)
app.include_router(tasks_router)
app.include_router(analysis_results_router)
app.include_router(compare_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "rsa-api", "status": "ok"}

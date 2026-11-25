import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import SessionLocal
from app.ml.loader import load_registered_models
from app.routers import analyze, auth, queries

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not getattr(app.state, "testing", False):
        try:
            with SessionLocal() as db:
                load_registered_models(db, Path(settings.model_dir))
        except Exception:
            logger.exception("Failed to load sentiment models during startup")
            raise

    yield


app = FastAPI(title="SentiBoard", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analyze.router)
app.include_router(queries.router)


@app.get("/health")
def health():
    return {"status": "ok"}

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_metadata_db
from app.routers import auth, sessions
from app.seed_analytics import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_metadata_db()
    seed_if_empty()
    yield


app = FastAPI(title="Intelligent Data Analysis System API", version="0.2.0", lifespan=lifespan)

_s = get_settings()
_origins = [o.strip() for o in _s.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

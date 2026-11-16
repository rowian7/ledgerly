from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import auth, stats, transactions

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For a portfolio project, creating tables on startup keeps setup to one command.
    # A production app would use migrations (e.g. Alembic) instead.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Ledgerly",
    description="A personal finance tracker: log income and expenses, see where your money goes.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(stats.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")

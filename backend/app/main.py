import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import agents, fixtures, sessions, transcripts, autoraters, classification, generation, settings, chat, devlogs
from app.services.log_service import dev_log


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    dev_log("DB", "info", "Database initialized")
    yield


app = FastAPI(title="Prompt Engineering Workbench", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def http_logging_middleware(request: Request, call_next):
    # Skip logging for the devlogs SSE endpoint to avoid recursion
    if request.url.path == "/api/devlogs/stream":
        return await call_next(request)

    method = request.method
    path = request.url.path
    dev_log("REQ", "info", f"{method} {path}")

    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = round((time.monotonic() - start) * 1000)

    level = "info" if response.status_code < 400 else ("warn" if response.status_code < 500 else "error")
    dev_log("RES", level, f"{response.status_code} {method} {path}", {"elapsed_ms": elapsed_ms})

    return response


app.include_router(agents.router)
app.include_router(fixtures.router)
app.include_router(sessions.router)
app.include_router(transcripts.router)
app.include_router(autoraters.router)
app.include_router(classification.router)
app.include_router(generation.router)
app.include_router(settings.router)
app.include_router(chat.router)
app.include_router(devlogs.router)


@app.get("/health")
def health():
    return {"status": "ok"}

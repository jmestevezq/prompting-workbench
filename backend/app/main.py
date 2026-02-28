from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import agents, fixtures, sessions, transcripts, autoraters, classification, generation, settings, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Prompt Engineering Workbench", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(fixtures.router)
app.include_router(sessions.router)
app.include_router(transcripts.router)
app.include_router(autoraters.router)
app.include_router(classification.router)
app.include_router(generation.router)
app.include_router(settings.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}

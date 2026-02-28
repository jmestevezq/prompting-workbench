# Build Progress

## Phase 1: Backend Core - COMPLETE
- database.py: All 13 tables created on startup
- config.py: Settings from .env
- schemas/: Pydantic models for all 6 domains
- services/gemini_client.py: google-genai wrapper with manual function calling
- routers/: CRUD for agents, fixtures, sessions, transcripts, autoraters, classification, generation (stub), settings
- main.py: FastAPI with CORS, lifespan, all routers
- Tested: all endpoints verified via curl

## Phase 2: Agent Runtime - IN PROGRESS
- Next: mock_tools.py, code_sandbox.py, agent_runtime.py, WebSocket chat handler

## TODOs
- generation.py POST /api/generate/transcripts is a stub (Phase 3)

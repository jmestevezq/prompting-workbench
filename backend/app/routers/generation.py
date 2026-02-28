from fastapi import APIRouter

router = APIRouter(prefix="/api/generate", tags=["generation"])

# POST /api/generate/transcripts — implemented in Phase 3 (batch eval)
# Stub endpoint for now so the router can be registered

from pydantic import BaseModel
from typing import Optional


class GenerateTranscriptsRequest(BaseModel):
    reference_transcript_ids: list[str]
    prompt: str
    count: int = 5
    model: str = "gemini-2.5-pro"


@router.post("/transcripts")
async def generate_transcripts(request: GenerateTranscriptsRequest):
    # TODO: Implement in Phase 3
    return {"status": "not_implemented", "message": "Transcript generation will be implemented in Phase 3"}

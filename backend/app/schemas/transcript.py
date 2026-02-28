from pydantic import BaseModel, Field
from typing import Optional, Any


class TranscriptCreate(BaseModel):
    name: Optional[str] = None
    content: str
    parsed_turns: Optional[Any] = None
    labels: dict = Field(default_factory=dict)
    source: str = "manual"
    tags: list[str] = Field(default_factory=list)


class TranscriptUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    parsed_turns: Optional[Any] = None
    labels: Optional[dict] = None
    tags: Optional[list[str]] = None


class TranscriptResponse(BaseModel):
    id: str
    name: Optional[str] = None
    content: str
    parsed_turns: Optional[Any] = None
    labels: dict
    source: str
    tags: Optional[list[str]] = None
    created_at: str


class TranscriptImport(BaseModel):
    transcripts: list[TranscriptCreate]

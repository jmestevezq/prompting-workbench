from pydantic import BaseModel, Field
from typing import Optional, Any


class SessionCreate(BaseModel):
    agent_id: str
    fixture_ids: list[str] = Field(default_factory=list)
    prompt_version_id: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    agent_id: str
    fixture_ids: Optional[list[str]] = None
    prompt_version_id: Optional[str] = None
    created_at: str


class TurnResponse(BaseModel):
    id: str
    session_id: str
    turn_index: int
    role: str
    content: str
    raw_request: Optional[Any] = None
    raw_response: Optional[Any] = None
    tool_calls: Optional[Any] = None
    tool_responses: Optional[Any] = None
    token_usage: Optional[Any] = None
    parent_turn_id: Optional[str] = None
    is_active: int = 1
    created_at: str

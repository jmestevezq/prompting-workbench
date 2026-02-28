from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AgentCreate(BaseModel):
    name: str
    system_prompt: str
    model: str = "gemini-2.5-pro"
    tool_definitions: list = Field(default_factory=list)


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    tool_definitions: Optional[list] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    system_prompt: str
    model: str
    tool_definitions: list
    created_at: str
    updated_at: str


class PromptVersionResponse(BaseModel):
    id: str
    agent_id: str
    system_prompt: str
    tool_definitions: Optional[list] = None
    version_hash: str
    label: Optional[str] = None
    created_at: str


class PromptVersionCreate(BaseModel):
    label: Optional[str] = None


class PromptVersionLabelUpdate(BaseModel):
    label: str

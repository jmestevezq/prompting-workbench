from pydantic import BaseModel, Field
from typing import Any, Optional
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
    agent_folder: Optional[str] = None
    active_version_id: Optional[str] = None
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


# --- Agent Version schemas ---

class AgentVersionResponse(BaseModel):
    id: str
    agent_id: str
    version_label: str
    source: str
    raw_template: Optional[str] = None
    variables: Optional[dict] = None
    variable_definitions: Optional[dict] = None
    system_prompt: str
    tool_details: Optional[list] = None
    widget_details: Optional[list] = None
    tools: Optional[list] = None
    is_base: bool = False
    created_at: str


class AgentVersionCreate(BaseModel):
    version_label: str
    system_prompt: str
    raw_template: Optional[str] = None
    variables: Optional[dict] = None
    variable_definitions: Optional[dict] = None
    tool_details: Optional[list] = None
    widget_details: Optional[list] = None
    tools: Optional[list] = None


class AgentImportResponse(BaseModel):
    agent_id: str
    version_id: str
    name: str
    version_label: str
    message: str


class AgentTemplateResponse(BaseModel):
    raw_template: Optional[str] = None
    variables: Optional[dict] = None
    variable_definitions: Optional[dict] = None
    system_prompt: str
    tool_details: Optional[list] = None
    widget_details: Optional[list] = None

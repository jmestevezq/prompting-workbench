from pydantic import BaseModel, Field
from typing import Optional, Any


class AutoraterCreate(BaseModel):
    name: str
    prompt: str
    model: str = "gemini-2.5-pro"
    output_schema: Optional[Any] = None


class AutoraterUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    model: Optional[str] = None
    output_schema: Optional[Any] = None


class AutoraterResponse(BaseModel):
    id: str
    name: str
    prompt: str
    model: str
    output_schema: Optional[Any] = None
    created_at: str


class EvalRunCreate(BaseModel):
    autorater_id: str
    transcript_ids: list[str]
    eval_tags: Optional[list[str]] = None


class EvalRunResponse(BaseModel):
    id: str
    autorater_id: str
    prompt_version_hash: Optional[str] = None
    transcript_ids: list[str]
    eval_tags: Optional[list[str]] = None
    status: str
    metrics: Optional[Any] = None
    created_at: str
    completed_at: Optional[str] = None


class EvalResultResponse(BaseModel):
    id: str
    run_id: str
    transcript_id: str
    predicted_labels: Any
    ground_truth_labels: Any
    match: Optional[bool] = None
    raw_response: Optional[Any] = None
    token_usage: Optional[Any] = None

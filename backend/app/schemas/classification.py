from pydantic import BaseModel, Field
from typing import Optional, Any


class GoldenTransactionCreate(BaseModel):
    set_name: str
    input_transactions: Any
    reference_transactions: Optional[Any] = None
    expected_output: Any
    tags: list[str] = Field(default_factory=list)


class GoldenTransactionUpdate(BaseModel):
    set_name: Optional[str] = None
    input_transactions: Optional[Any] = None
    reference_transactions: Optional[Any] = None
    expected_output: Optional[Any] = None
    tags: Optional[list[str]] = None


class GoldenTransactionResponse(BaseModel):
    id: str
    set_name: str
    input_transactions: Any
    reference_transactions: Optional[Any] = None
    expected_output: Any
    tags: Optional[list[str]] = None
    created_at: str


class GoldenTransactionImport(BaseModel):
    items: list[GoldenTransactionCreate]


class ClassificationPromptCreate(BaseModel):
    name: str
    prompt_template: str
    model: str = "gemini-2.5-pro"


class ClassificationPromptUpdate(BaseModel):
    name: Optional[str] = None
    prompt_template: Optional[str] = None
    model: Optional[str] = None


class ClassificationPromptResponse(BaseModel):
    id: str
    name: str
    prompt_template: str
    model: str
    created_at: str


class ClassificationRunCreate(BaseModel):
    prompt_id: str
    golden_set_name: str


class ClassificationRunResponse(BaseModel):
    id: str
    prompt_id: str
    prompt_version_hash: Optional[str] = None
    golden_set_name: Optional[str] = None
    status: str
    metrics: Optional[Any] = None
    created_at: str
    completed_at: Optional[str] = None


class ClassificationResultResponse(BaseModel):
    id: str
    run_id: str
    golden_id: str
    predicted_output: Any
    match_details: Optional[Any] = None
    raw_response: Optional[Any] = None
    token_usage: Optional[Any] = None

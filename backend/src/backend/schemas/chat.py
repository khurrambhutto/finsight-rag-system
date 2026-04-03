from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    model: str | None = Field(default=None, max_length=256)


class ChatMessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    model: str | None = None
    created_at: str


class ChatThreadSummary(BaseModel):
    id: str
    title: str
    preview: str | None = None
    created_at: str
    updated_at: str


class ChatThreadDetail(ChatThreadSummary):
    messages: list[ChatMessageResponse] = Field(default_factory=list)


class ProviderConfigResponse(BaseModel):
    name: str
    provider_type: str
    base_url: str
    default_model: str
    is_local: bool = True


class ProviderTestResponse(BaseModel):
    ok: bool
    message: str


class OllamaModelsResponse(BaseModel):
    models: list[str]

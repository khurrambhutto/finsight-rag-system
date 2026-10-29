"""Validated answer-provider choices shared by the API and generation layer."""
import os
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

FREE_ROUTER = 'openrouter/free'
FREE_MODEL_PATTERN = r'^(openrouter/free|[a-zA-Z0-9._/-]+:free)$'
GEMINI_MODEL = 'gemini-3.5-flash-lite'


class OllamaConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    provider: Literal['ollama'] = 'ollama'


class OpenRouterConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    provider: Literal['openrouter'] = 'openrouter'
    model: str = Field(default=FREE_ROUTER, pattern=FREE_MODEL_PATTERN, max_length=200)
    api_key: SecretStr | None = None


class GeminiConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    provider: Literal['gemini'] = 'gemini'
    model: str = Field(default=GEMINI_MODEL, pattern=r'^gemini-[a-zA-Z0-9.-]+$', max_length=200)
    api_key: SecretStr | None = None


GenerationConfig = Annotated[OllamaConfig | OpenRouterConfig | GeminiConfig, Field(discriminator='provider')]


def ollama_model():
    return os.getenv('OLLAMA_MODEL', 'bonsai-2:2b')


class GenerationError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code

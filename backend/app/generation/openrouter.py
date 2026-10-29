"""OpenRouter free-model discovery and chat transport. Keys are never persisted."""
import json
import os
import urllib.error
import urllib.request

from pydantic import BaseModel, Field, ValidationError

from app.generation.config import FREE_ROUTER, GenerationError, OpenRouterConfig

API_URL = 'https://openrouter.ai/api/v1'


class CatalogModel(BaseModel):
    id: str
    name: str
    supported_parameters: list[str] = Field(default_factory=list)


class ModelCatalog(BaseModel):
    data: list[CatalogModel]


class Message(BaseModel):
    content: str


class Choice(BaseModel):
    message: Message


class Completion(BaseModel):
    model: str
    choices: list[Choice] = Field(min_length=1)


def configured_key():
    return os.getenv('OPENROUTER_API_KEY', '').strip()


def api_key(config: OpenRouterConfig):
    key = (config.api_key.get_secret_value().strip() if config.api_key else '') or configured_key()
    if not key:
        raise GenerationError('Enter an OpenRouter API key or set OPENROUTER_API_KEY on the backend.', 400)
    if not key.isascii() or any(character.isspace() or ord(character) < 32 for character in key):
        raise GenerationError('Enter a valid OpenRouter API key.', 400)
    return key


def free_models():
    try:
        with urllib.request.urlopen(API_URL + '/models', timeout=15) as response:
            catalog = ModelCatalog.model_validate(json.load(response))
        models = [{'id': model.id, 'name': model.name} for model in catalog.data
                  if model.id.endswith(':free') and 'response_format' in model.supported_parameters]
        return [{'id': FREE_ROUTER, 'name': 'Auto · Free models'}] + sorted(models, key=lambda model: model['name'])
    except (urllib.error.URLError, TimeoutError, ValueError, ValidationError):
        raise GenerationError('Could not load OpenRouter models. Try again.') from None


def complete(prompt: str, config: OpenRouterConfig):
    body = {'model': config.model, 'stream': False, 'temperature': 0, 'max_tokens': 2048,
            'response_format': {'type': 'json_object'},
            'messages': [{'role': 'user', 'content': prompt}]}
    request = urllib.request.Request(API_URL + '/chat/completions', data=json.dumps(body).encode(),
        headers={'Authorization': 'Bearer ' + api_key(config), 'Content-Type': 'application/json',
                 'X-OpenRouter-Title': 'FinSight AI'})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = json.load(response)
        if isinstance(raw, dict) and 'error' in raw:
            raise GenerationError('OpenRouter could not complete the request. Try another free model.', 502)
        completion = Completion.model_validate(raw)
        return completion.choices[0].message.content, completion.model
    except urllib.error.HTTPError as exc:
        exc.close()
        messages = {
            400: 'OpenRouter rejected the request. Try another free model.',
            401: 'OpenRouter rejected the API key. Check your key.',
            402: 'OpenRouter account quota is unavailable. Check your account or try another free model.',
            403: 'OpenRouter denied this request. Check your key and account permissions.',
            404: 'This free model is unavailable. Refresh the models or choose Auto.',
            429: 'OpenRouter free-model rate limit reached. Wait and try again, or choose another free model.',
        }
        raise GenerationError(messages.get(exc.code, 'OpenRouter is unavailable. Try another free model.'),
                              429 if exc.code == 429 else 502) from None
    except (urllib.error.URLError, TimeoutError):
        raise GenerationError('OpenRouter timed out or could not be reached. Try again.') from None
    except (ValueError, ValidationError):
        raise GenerationError('OpenRouter returned an invalid response. Try another free model.', 502) from None

"""Direct Gemini API transport, with credentials passed only in headers."""
import json
import os
import urllib.error
import urllib.request

from pydantic import BaseModel, Field

from app.generation.config import GEMINI_MODEL, GeminiConfig, GenerationError

API_URL = 'https://generativelanguage.googleapis.com/v1beta/models'
MODELS = [
    {'id': GEMINI_MODEL, 'name': 'Gemini 3.5 Flash-Lite'},
    {'id': 'gemini-3.8-flash', 'name': 'Gemini 3.8 Flash'},
]


class Part(BaseModel):
    text: str = ''
    thought: bool = False


class Content(BaseModel):
    parts: list[Part] = Field(default_factory=list)


class Candidate(BaseModel):
    content: Content | None = None
    finishReason: str = ''


class Completion(BaseModel):
    candidates: list[Candidate] = Field(default_factory=list)
    modelVersion: str | None = None


def configured_key():
    return os.getenv('GEMINI_API_KEY', '').strip()


def api_key(config: GeminiConfig):
    key = (config.api_key.get_secret_value().strip() if config.api_key else '') or configured_key()
    if not key:
        raise GenerationError('Enter a Gemini API key or set GEMINI_API_KEY on the backend.', 400)
    if not key.isascii() or any(character.isspace() or ord(character) < 32 for character in key):
        raise GenerationError('Enter a valid Gemini API key.', 400)
    return key


def complete(prompt: str, config: GeminiConfig):
    schema = {'type': 'object', 'properties': {'answer': {'type': 'string'},
              'citations': {'type': 'array', 'items': {'type': 'integer'}}},
              'required': ['answer', 'citations']}
    body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {'responseFormat': {'text': {'mimeType': 'APPLICATION_JSON', 'schema': schema}},
                                 'maxOutputTokens': 4096}}
    request = urllib.request.Request(f'{API_URL}/{config.model}:generateContent', data=json.dumps(body).encode(),
        headers={'x-goog-api-key': api_key(config), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            completion = Completion.model_validate(json.load(response))
        if not completion.candidates:
            raise GenerationError('Gemini returned no answer. The request may have been blocked. Try rephrasing it.', 502)
        candidate = completion.candidates[0]
        if candidate.finishReason != 'STOP' or not candidate.content:
            raise GenerationError('Gemini could not finish the answer. Try another model or rephrase the question.', 502)
        text = ''.join(part.text for part in candidate.content.parts if not part.thought)
        if not text.strip():
            raise GenerationError('Gemini returned no answer text. Try another model.', 502)
        return text, completion.modelVersion or config.model
    except urllib.error.HTTPError as exc:
        exc.close()
        messages = {
            400: 'Gemini rejected the request. Check your API key and selected model.',
            401: 'Gemini rejected the API key. Check your key.',
            403: 'Gemini denied access. Check your API key, project permissions, and regional availability.',
            404: 'This Gemini model is unavailable. Choose another model.',
            429: 'Gemini rate limit or quota reached. Check your quota, wait, and try again.',
        }
        raise GenerationError(messages.get(exc.code, 'Gemini is unavailable. Try again later.'),
                              429 if exc.code == 429 else 502) from None
    except (urllib.error.URLError, TimeoutError):
        raise GenerationError('Gemini timed out or could not be reached. Try again.') from None
    except ValueError:
        raise GenerationError('Gemini returned an invalid response. Try another model.', 502) from None

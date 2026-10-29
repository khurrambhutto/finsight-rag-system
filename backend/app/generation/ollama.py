"""Local Ollama chat transport."""
import json
import os
import urllib.error
import urllib.request

from app.generation.config import GenerationError, ollama_model


def complete(prompt: str):
    model = ollama_model()
    body = {'model': model, 'stream': False, 'format': 'json', 'options': {'temperature': 0},
            'messages': [{'role': 'user', 'content': prompt}]}
    url = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
    request = urllib.request.Request(url + '/api/chat', data=json.dumps(body).encode(),
                                    headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            raw = json.load(response)
        content = raw['message']['content']
        if not isinstance(content, str):
            raise ValueError('Invalid content')
        return content, model
    except (urllib.error.URLError, TimeoutError):
        raise GenerationError(f'Could not reach Ollama or model {model}. Check the service and model installation.') from None
    except (ValueError, KeyError, TypeError):
        raise GenerationError('Ollama returned an invalid response. Try again.', 502) from None

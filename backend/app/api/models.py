from fastapi import APIRouter, HTTPException

from app.generation.config import GenerationError
from app.generation.openrouter import configured_key, free_models
from app.generation import gemini

router = APIRouter()


@router.get('/models/openrouter')
def list_openrouter_models():
    try:
        return {'models': free_models(), 'api_key_configured': bool(configured_key())}
    except GenerationError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None


@router.get('/models/gemini')
def list_gemini_models():
    return {'models': gemini.MODELS, 'api_key_configured': bool(gemini.configured_key())}

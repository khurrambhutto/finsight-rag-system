from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from app.main import connect
from app.generation.config import GenerationConfig, GenerationError, GeminiConfig, OllamaConfig, OpenRouterConfig, ollama_model

router = APIRouter()


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_id: str
    generation: GenerationConfig = Field(default_factory=OllamaConfig)

    @field_validator('question')
    @classmethod
    def nonempty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Enter a question.')
        return value


@router.post('/questions')
def ask(request: QuestionRequest):
    with connect() as db:
        document = db.execute('SELECT * FROM documents WHERE id = ?', (request.document_id,)).fetchone()
        if not document:
            raise HTTPException(404, 'Report not found.')
        if document['status'] != 'ready':
            raise HTTPException(409, 'The report must be ready before it can be searched.')
        chunks = [dict(row) for row in db.execute('SELECT id, page, section, content_type, text FROM chunks WHERE document_id = ? ORDER BY position', (request.document_id,))]
    if isinstance(request.generation, (OpenRouterConfig, GeminiConfig)):
        if isinstance(request.generation, GeminiConfig):
            from app.generation.gemini import api_key
        else:
            from app.generation.openrouter import api_key
        try:
            api_key(request.generation)
        except GenerationError as exc:
            raise HTTPException(exc.status_code, str(exc)) from None
    try:
        from app.retrieval.search import search
        from app.generation.llm import answer, GeneratedAnswer, INSUFFICIENT
        passages = search(dict(document), chunks, request.question)
        model = ollama_model() if isinstance(request.generation, OllamaConfig) else request.generation.model
        result = answer(request.question, passages, request.generation, document=dict(document)) if passages else GeneratedAnswer(INSUFFICIENT, [], model)
        return {'answer': result.text, 'citations': result.citations, 'retrieved_passages': passages, 'model': result.model}
    except GenerationError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception('Question failed')
        raise HTTPException(503, str(exc) if isinstance(exc, RuntimeError) else 'Search is unavailable. Check Qdrant and embedding model setup.') from exc

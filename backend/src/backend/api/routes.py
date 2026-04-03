from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sse_starlette import EventSourceResponse, JSONServerSentEvent

from backend.core.auth import get_current_user
from backend.core.config import Settings, get_settings
from backend.schemas.auth import AuthenticatedUser, UserProfile
from backend.schemas.chat import (
    ChatRequest,
    ChatThreadDetail,
    ChatThreadSummary,
    OllamaModelsResponse,
    ProviderConfigResponse,
    ProviderTestResponse,
)
from backend.services.chat import build_chat_messages, stream_chat_completion
from backend.services.chat_store import ChatStore, get_chat_store
from backend.services.providers import (
    get_provider_config,
    list_ollama_models,
    resolve_chat_model,
    test_provider_connection,
)

router = APIRouter()


def _get_chat_store(settings: Settings = Depends(get_settings)) -> ChatStore:
    return get_chat_store(settings.sqlite_path)


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/me", response_model=UserProfile)
async def me(user: AuthenticatedUser = Depends(get_current_user)) -> UserProfile:
    display_name = user.email.split("@")[0] if user.email else "Clerk User"
    return UserProfile(id=user.user_id, email=user.email, display_name=display_name)


@router.get("/providers", response_model=ProviderConfigResponse)
async def providers(
    _: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ProviderConfigResponse:
    return get_provider_config(settings)


@router.post("/providers/test", response_model=ProviderTestResponse)
async def providers_test(
    _: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ProviderTestResponse:
    try:
        return await test_provider_connection(settings)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/providers/models", response_model=OllamaModelsResponse)
async def providers_models(
    _: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> OllamaModelsResponse:
    try:
        models = await list_ollama_models(settings)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not list Ollama models at {settings.ollama_base_url}: {exc!s}",
        ) from exc
    return OllamaModelsResponse(models=models)


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    _: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> EventSourceResponse:
    try:
        model_id = await resolve_chat_model(settings, payload.model)
    except ValueError as exc:
        detail = str(exc)
        status_code = 400 if "not installed in Ollama" in detail else 502
        raise HTTPException(status_code=status_code, detail=detail) from exc

    async def event_generator() -> AsyncIterator[JSONServerSentEvent]:
        try:
            yield JSONServerSentEvent({"message": "stream-started"}, event="ready")
            async for token in stream_chat_completion(
                settings=settings,
                messages=build_chat_messages(history=[], user_message=payload.message),
                model=model_id,
            ):
                yield JSONServerSentEvent({"content": token}, event="chunk")
            yield JSONServerSentEvent({"message": "stream-complete"}, event="done")
        except Exception as exc:  # noqa: BLE001
            yield JSONServerSentEvent({"message": str(exc)}, event="error")

    return EventSourceResponse(event_generator())


@router.get("/chat/threads", response_model=list[ChatThreadSummary])
async def list_chat_threads(
    user: AuthenticatedUser = Depends(get_current_user),
    store: ChatStore = Depends(_get_chat_store),
) -> list[ChatThreadSummary]:
    return [ChatThreadSummary.model_validate(item) for item in store.list_threads(user_id=user.user_id)]


@router.post("/chat/threads", response_model=ChatThreadSummary)
async def create_chat_thread(
    user: AuthenticatedUser = Depends(get_current_user),
    store: ChatStore = Depends(_get_chat_store),
) -> ChatThreadSummary:
    return ChatThreadSummary.model_validate(store.create_thread(user_id=user.user_id))


@router.get("/chat/threads/{thread_id}", response_model=ChatThreadDetail)
async def get_chat_thread(
    thread_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    store: ChatStore = Depends(_get_chat_store),
) -> ChatThreadDetail:
    try:
        thread = store.get_thread(user_id=user.user_id, thread_id=thread_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chat thread not found.") from exc
    return ChatThreadDetail.model_validate(thread)


@router.delete("/chat/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_thread(
    thread_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    store: ChatStore = Depends(_get_chat_store),
) -> Response:
    try:
        store.delete_thread(user_id=user.user_id, thread_id=thread_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chat thread not found.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/chat/threads/{thread_id}/stream")
async def stream_chat_thread(
    thread_id: str,
    payload: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    store: ChatStore = Depends(_get_chat_store),
) -> EventSourceResponse:
    try:
        history = store.get_messages(user_id=user.user_id, thread_id=thread_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chat thread not found.") from exc

    try:
        model_id = await resolve_chat_model(settings, payload.model)
    except ValueError as exc:
        detail = str(exc)
        status_code = 400 if "not installed in Ollama" in detail else 502
        raise HTTPException(status_code=status_code, detail=detail) from exc

    store.set_thread_title_from_message(
        user_id=user.user_id,
        thread_id=thread_id,
        content=payload.message,
    )
    store.add_message(
        user_id=user.user_id,
        thread_id=thread_id,
        role="user",
        content=payload.message,
        model=model_id,
    )
    model_messages = build_chat_messages(history=history, user_message=payload.message)

    async def event_generator() -> AsyncIterator[JSONServerSentEvent]:
        assistant_chunks: list[str] = []
        try:
            yield JSONServerSentEvent({"message": "stream-started"}, event="ready")
            async for token in stream_chat_completion(
                settings=settings,
                messages=model_messages,
                model=model_id,
            ):
                assistant_chunks.append(token)
                yield JSONServerSentEvent({"content": token}, event="chunk")
            assistant_message = "".join(assistant_chunks).strip()
            if assistant_message:
                store.add_message(
                    user_id=user.user_id,
                    thread_id=thread_id,
                    role="assistant",
                    content=assistant_message,
                    model=model_id,
                )
            yield JSONServerSentEvent({"message": "stream-complete"}, event="done")
        except Exception as exc:  # noqa: BLE001
            yield JSONServerSentEvent({"message": str(exc)}, event="error")

    return EventSourceResponse(event_generator())

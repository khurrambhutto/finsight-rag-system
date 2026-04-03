from collections.abc import AsyncIterator

from litellm import acompletion

from backend.core.config import Settings


SYSTEM_PROMPT = """You are a concise AI assistant for a RAG application.
Answer clearly and directly. If context is missing, say what is missing instead of inventing details."""


def build_chat_messages(
    *,
    history: list[dict[str, str | None]],
    user_message: str,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


async def stream_chat_completion(
    *,
    settings: Settings,
    messages: list[dict[str, str]],
    model: str,
) -> AsyncIterator[str]:
    response = await acompletion(
        model=model,
        api_base=settings.ollama_base_url,
        stream=True,
        messages=messages,
    )

    async for chunk in response:
        choices = chunk.get("choices") or []
        if not choices:
            continue

        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if content:
            yield content

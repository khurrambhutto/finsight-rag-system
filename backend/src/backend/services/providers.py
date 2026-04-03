import httpx

from backend.core.config import Settings
from backend.schemas.chat import ProviderConfigResponse, ProviderTestResponse


async def list_ollama_models(settings: Settings) -> list[str]:
    url = settings.ollama_base_url.rstrip("/") + "/api/tags"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    payload = response.json()
    names: list[str] = []
    for item in payload.get("models") or []:
        name = item.get("name")
        if isinstance(name, str) and name:
            names.append(f"ollama/{name}")
    return sorted(set(names))


async def resolve_chat_model(settings: Settings, requested: str | None) -> str:
    try:
        allowed = await list_ollama_models(settings)
    except httpx.HTTPError as exc:
        msg = f"Could not reach Ollama at {settings.ollama_base_url}: {exc!s}"
        raise ValueError(msg) from exc

    if not allowed:
        raise ValueError(
            "Ollama returned no models. Start Ollama and pull a model (e.g. `ollama pull llama3.2`)."
        )

    default = (
        settings.ollama_model
        if settings.ollama_model in allowed
        else allowed[0]
    )
    if not requested or not requested.strip():
        return default

    cleaned = requested.strip()
    if cleaned not in allowed:
        raise ValueError(
            f"Model '{cleaned}' is not installed in Ollama. Choose a model from the list in Settings."
        )
    return cleaned


def get_provider_config(settings: Settings) -> ProviderConfigResponse:
    return ProviderConfigResponse(
        name=settings.provider_name,
        provider_type=settings.provider_type,
        base_url=settings.ollama_base_url,
        default_model=settings.ollama_model,
        is_local=True,
    )


async def test_provider_connection(settings: Settings) -> ProviderTestResponse:
    url = settings.ollama_base_url.rstrip("/") + "/api/tags"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    return ProviderTestResponse(
        ok=True,
        message=f"Connected to {settings.provider_name} at {settings.ollama_base_url}.",
    )

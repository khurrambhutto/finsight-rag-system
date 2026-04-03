from collections.abc import Mapping

from clerk_backend_api.sdk import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions, TokenType
from fastapi import Depends, HTTPException, Request, status

from backend.core.config import Settings, get_settings
from backend.schemas.auth import AuthenticatedUser


class ClerkRequestAdapter:
    def __init__(self, headers: Mapping[str, str]) -> None:
        self._headers = headers

    @property
    def headers(self) -> Mapping[str, str]:
        return self._headers


def get_clerk_client(settings: Settings = Depends(get_settings)) -> Clerk:
    if not settings.clerk_secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_SECRET_KEY is not configured.",
        )
    return Clerk(bearer_auth=settings.clerk_secret_key)


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    clerk_client: Clerk = Depends(get_clerk_client),
) -> AuthenticatedUser:
    state = clerk_client.authenticate_request(
        ClerkRequestAdapter(headers=request.headers),
        AuthenticateRequestOptions(
            secret_key=settings.clerk_secret_key,
            jwt_key=settings.clerk_jwt_key,
            authorized_parties=settings.clerk_authorized_parties or None,
            accepts_token=[TokenType.SESSION_TOKEN.value],
        ),
    )

    if not state.is_authenticated or state.payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=state.message or "Unauthorized",
        )

    return AuthenticatedUser(
        user_id=state.payload.get("sub", ""),
        session_id=state.payload.get("sid", ""),
        email=state.payload.get("email"),
    )

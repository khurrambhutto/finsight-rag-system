from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    user_id: str
    session_id: str
    email: str | None = None


class UserProfile(BaseModel):
    id: str
    email: str | None = None
    display_name: str

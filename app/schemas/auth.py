from typing import Optional
from pydantic import BaseModel
from app.models.user import UserRole

try:
    import email_validator  # noqa: F401
    from pydantic import EmailStr
except ImportError:
    EmailStr = str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    full_name: str
    email: str


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None
    type: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

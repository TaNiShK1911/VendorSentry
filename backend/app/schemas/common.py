"""
Common schemas shared across multiple endpoints.
"""
from typing import Generic, TypeVar, List
from pydantic import BaseModel


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper"""
    items: List[T]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class LoginRequest(BaseModel):
    """Login credentials"""
    email: str
    password: str


class SignupRequest(BaseModel):
    """User registration data"""
    email: str
    password: str
    first_name: str
    last_name: str
    role: str


class LoginResponse(BaseModel):
    """JWT token response with user data"""
    access_token: str
    token_type: str = "bearer"
    role: str
    user: dict  # Contains: id, email, first_name, last_name, role


class TokenData(BaseModel):
    """Decoded JWT token data"""
    email: str
    role: str

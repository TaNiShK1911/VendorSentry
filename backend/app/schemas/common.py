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
    username: str
    password: str


class LoginResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str
    role: str


class TokenData(BaseModel):
    """Decoded JWT token data"""
    username: str
    role: str

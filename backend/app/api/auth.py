"""Authentication API endpoints"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings

settings = get_settings()
from app.core.security import create_access_token, decode_access_token
from app.schemas import LoginRequest, LoginResponse, TokenData

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Mock user database for hackathon (in production, use real user table)
MOCK_USERS = {
    "ciso@vendorsentry.com": {
        "password": "ciso123",  # In production: hashed
        "role": "ciso"
    },
    "procurement@vendorsentry.com": {
        "password": "proc123",
        "role": "procurement"
    },
    "auditor@vendorsentry.com": {
        "password": "audit123",
        "role": "auditor"
    },
    # Demo/hackathon shorthand credentials
    "admin": {
        "password": "admin123",
        "role": "ciso"
    },
    "admin@vendorsentry.com": {
        "password": "admin123",
        "role": "ciso"
    }
}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    Dependency to extract current user from JWT token.

    Can be used in route handlers that require authentication.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return TokenData(
        username=payload.get("sub"),
        role=payload.get("role")
    )


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    """
    Basic authentication endpoint.

    Returns JWT token with role information.
    Per BACKEND_INTEGRATION.md §8, this is minimal hackathon-scope auth.

    Demo credentials:
    - admin / admin123  (CISO role)
    - ciso@vendorsentry.com / ciso123
    - procurement@vendorsentry.com / proc123
    - auditor@vendorsentry.com / audit123
    """
    user = MOCK_USERS.get(credentials.username)

    if not user or user["password"] != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": credentials.username, "role": user["role"]},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user["role"]
    )


@router.get("/me", response_model=TokenData)
def get_me(current_user: TokenData = Depends(get_current_user)):
    """Get current authenticated user info from JWT token."""
    return current_user

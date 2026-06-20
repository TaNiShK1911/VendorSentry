"""Authentication API endpoints"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings

settings = get_settings()
from app.core.security import create_access_token, decode_access_token
from app.schemas import LoginRequest, SignupRequest, LoginResponse, TokenData

router = APIRouter()
security = HTTPBearer()

# Mock user database for hackathon (in production, use real user table)
MOCK_USERS = {
    # Original demo users
    "ciso@vendorsentry.demo": {
        "password": "demo123456",
        "role": "ciso",
        "first_name": "Demo",
        "last_name": "CISO"
    },
    "procurement@vendorsentry.demo": {
        "password": "demo123456",
        "role": "procurement",
        "first_name": "Demo",
        "last_name": "Procurement"
    },
    "auditor@vendorsentry.demo": {
        "password": "demo123456",
        "role": "auditor",
        "first_name": "Demo",
        "last_name": "Auditor"
    },
    # Frontend quick-login demo users
    "ciso@company.com": {
        "password": "password123",
        "role": "ciso",
        "first_name": "Alex",
        "last_name": "Chen"
    },
    "procurement@company.com": {
        "password": "password123",
        "role": "procurement",
        "first_name": "Sarah",
        "last_name": "Miller"
    },
    "auditor@company.com": {
        "password": "password123",
        "role": "auditor",
        "first_name": "James",
        "last_name": "Wilson"
    },
}


def _build_user_data(email: str, user: dict) -> dict:
    """Build the user object for API responses."""
    return {
        "id": email,
        "email": email,
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "name": f"{user['first_name']} {user['last_name']}",
        "role": user["role"],
    }


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    """
    Basic authentication endpoint.
    Returns JWT token with role information.
    """
    user = MOCK_USERS.get(credentials.email)

    if not user or user["password"] != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": credentials.email, "role": user["role"]},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )

    user_data = _build_user_data(credentials.email, user)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user["role"],
        user=user_data
    )


@router.post("/signup", response_model=LoginResponse)
def signup(request: SignupRequest):
    """User registration endpoint."""
    if request.email in MOCK_USERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if request.role not in ["ciso", "procurement", "auditor"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be: ciso, procurement, or auditor"
        )

    MOCK_USERS[request.email] = {
        "password": request.password,
        "role": request.role,
        "first_name": request.first_name,
        "last_name": request.last_name
    }

    access_token = create_access_token(
        data={"sub": request.email, "role": request.role},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )

    user_data = _build_user_data(request.email, MOCK_USERS[request.email])

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=request.role,
        user=user_data
    )


@router.get("/me")
def get_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current user info from JWT token.
    Frontend calls this on every page load to validate the token.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    email = payload.get("sub")
    role = payload.get("role")

    # Look up user in mock DB
    user = MOCK_USERS.get(email)
    if user:
        return _build_user_data(email, user)

    # Fallback if user not found in mock DB (e.g. registered in another process)
    return {
        "id": email,
        "email": email,
        "first_name": email.split("@")[0].capitalize(),
        "last_name": "",
        "name": email.split("@")[0].capitalize(),
        "role": role,
    }


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Dependency to extract current user from JWT token."""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return TokenData(
        email=payload.get("sub"),
        role=payload.get("role")
    )

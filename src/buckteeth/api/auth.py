import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from buckteeth.api.deps import get_current_user, get_session
from buckteeth.auth import create_access_token, hash_password, verify_password
from buckteeth.models.user import User

router = APIRouter(prefix="/v1/auth", tags=["auth"])


# --- Request / Response schemas ---


class RegisterRequest(BaseModel):
    practice_name: str
    email: str
    password: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class InviteRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    practice_name: str | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class InviteResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str


# --- Endpoints ---


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    # Check if email already exists
    result = await session.execute(
        select(User).where(User.email == body.email)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    tenant_id = uuid.uuid4()

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        role="admin",
        tenant_id=tenant_id,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
    )

    return AuthResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            practice_name=body.practice_name,
        ),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
    )

    return AuthResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).where(User.id == uuid.UUID(current_user["user_id"]))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
    )


@router.post("/invite", response_model=InviteResponse, status_code=201)
async def invite_user(
    body: InviteRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can invite users")

    if body.role not in ("admin", "provider", "staff"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be admin, provider, or staff")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Check if email already exists
    result = await session.execute(
        select(User).where(User.email == body.email)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        role=body.role,
        tenant_id=uuid.UUID(current_user["tenant_id"]),
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)

    return InviteResponse(
        id=user.id,
        email=user.email,
        role=user.role,
    )

import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from buckteeth.auth import decode_token
from buckteeth.database import get_db


async def get_current_user(request: Request) -> dict:
    """Extract user info from JWT Bearer token.

    Returns dict with user_id, tenant_id, and role.
    Raises 401 if no valid token is present.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return {
        "user_id": payload["sub"],
        "tenant_id": payload["tenant_id"],
        "role": payload["role"],
    }


async def get_tenant_id(
    request: Request,
    x_tenant_id: Optional[str] = Header(None),
) -> uuid.UUID:
    """Extract tenant ID from JWT token or fall back to X-Tenant-ID header.

    Checks for Authorization: Bearer <token> first. If present, uses the
    tenant_id from the JWT claims. Otherwise falls back to the X-Tenant-ID
    header for backward compatibility.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = decode_token(token)
            return uuid.UUID(payload["tenant_id"])
        except (ValueError, KeyError):
            raise HTTPException(status_code=401, detail="Invalid token")

    # Fall back to X-Tenant-ID header
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-ID header or Authorization token")
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    return session

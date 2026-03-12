import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from buckteeth.database import get_db


async def get_tenant_id(x_tenant_id: str = Header(...)) -> uuid.UUID:
    """Extract tenant ID from header. In production, this comes from JWT claims."""
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    return session

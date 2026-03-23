"""API endpoints for the coding update agent."""

from fastapi import APIRouter

from buckteeth.coding.update_agent import CodingUpdateAgent, UPDATE_SOURCES
from buckteeth.config import settings

router = APIRouter(prefix="/v1/updates", tags=["updates"])


def _get_agent() -> CodingUpdateAgent:
    return CodingUpdateAgent(api_key=settings.anthropic_api_key)


@router.get("/status")
async def get_update_status():
    """Get current coding update status — what's applied, what's pending."""
    agent = _get_agent()
    return agent.get_update_status()


@router.post("/check")
async def check_for_updates():
    """Run an update check against known sources."""
    agent = _get_agent()
    result = agent.check_known_updates()
    return result.to_dict()


@router.get("/sources")
async def list_update_sources():
    """List all monitored update sources."""
    return UPDATE_SOURCES


@router.post("/{title}/apply")
async def mark_update_applied(title: str):
    """Mark a specific update as applied."""
    agent = _get_agent()
    success = agent.mark_applied(title)
    return {"applied": success, "title": title}

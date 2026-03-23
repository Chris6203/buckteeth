"""
Coding Update Agent

Automated agent that checks for and applies updates to:
- CDT code changes (annual ADA updates)
- Payer rule changes (frequency limits, preauth requirements)
- Documentation requirement changes
- CARC/RARC code updates

Can be run manually or scheduled via cron.

Sources checked:
- ADA CDT update announcements
- Major payer bulletins (Delta Dental, MetLife, Cigna, etc.)
- CMS/Medicaid updates
- Industry publications

Uses Claude to analyze found updates and determine if our knowledge
base needs changes.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

UPDATE_CHECK_FILE = os.environ.get(
    "UPDATE_CHECK_FILE", "/opt/buckteeth/coding_updates.json"
)


@dataclass
class CodingUpdate:
    """A single coding update found by the agent."""

    source: str  # Where the update was found
    category: str  # "cdt_code", "payer_rule", "documentation", "denial_code"
    severity: str  # "breaking" (must update), "important", "informational"
    title: str
    description: str
    effective_date: str  # When the change takes effect
    action_required: str  # What needs to change in our system
    applied: bool = False
    found_date: str = ""

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "effective_date": self.effective_date,
            "action_required": self.action_required,
            "applied": self.applied,
            "found_date": self.found_date,
        }


@dataclass
class UpdateCheckResult:
    """Result of an update check run."""

    checked_at: str
    sources_checked: list[str]
    updates_found: list[CodingUpdate]
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "checked_at": self.checked_at,
            "sources_checked": self.sources_checked,
            "updates_found": [u.to_dict() for u in self.updates_found],
            "errors": self.errors,
            "total_updates": len(self.updates_found),
            "breaking_updates": sum(
                1 for u in self.updates_found if u.severity == "breaking"
            ),
        }


# ── Known Update Sources ──────────────────────────────────────────────

UPDATE_SOURCES = {
    "ada_cdt": {
        "name": "ADA CDT Code Updates",
        "url": "https://www.ada.org/publications/cdt",
        "check_frequency": "monthly",
        "description": "Annual CDT code additions, revisions, and deletions from the ADA Code Maintenance Committee. New codes take effect January 1 each year.",
    },
    "delta_dental": {
        "name": "Delta Dental Provider Bulletins",
        "url": "https://www1.deltadentalins.com/dentists/fyi-online.html",
        "check_frequency": "weekly",
        "description": "Delta Dental policy changes, coding tips, and documentation requirements.",
    },
    "cigna_dental": {
        "name": "Cigna Dental Provider Updates",
        "url": "https://www.cigna.com/dental-providers",
        "check_frequency": "weekly",
        "description": "Cigna dental policy updates and coding guidelines.",
    },
    "metlife_dental": {
        "name": "MetLife Dental Provider Resources",
        "url": "https://www.metlife.com/dental-providers",
        "check_frequency": "weekly",
        "description": "MetLife dental benefit and coding updates.",
    },
    "uhc_dental": {
        "name": "UHC Dental Provider Updates",
        "url": "https://www.uhcprovider.com/dental",
        "check_frequency": "weekly",
        "description": "United Healthcare dental policy and utilization review updates.",
    },
    "cms_medicaid": {
        "name": "CMS Medicaid Dental Updates",
        "url": "https://www.medicaid.gov/medicaid/benefits/dental-care",
        "check_frequency": "monthly",
        "description": "Federal Medicaid dental benefit changes and state plan amendments.",
    },
    "ada_news": {
        "name": "ADA News - Coding & Insurance",
        "url": "https://adanews.ada.org",
        "check_frequency": "weekly",
        "description": "ADA news articles about coding changes, insurance issues, and practice management.",
    },
}

# ── CDT 2026 Known Updates (pre-loaded) ───────────────────────────────

CDT_2026_UPDATES = [
    CodingUpdate(
        source="ADA CDT 2026",
        category="cdt_code",
        severity="breaking",
        title="D1352 Deleted - Preventive Resin Restoration",
        description="Code D1352 (preventive resin restoration) has been deleted. "
        "Practices should use revised D2391 (resin-based composite, one surface, posterior) instead.",
        effective_date="2026-01-01",
        action_required="Remove D1352 from code selection. Update AI prompts to suggest D2391 for preventive resin restorations.",
        applied=True,
        found_date="2025-12-24",
    ),
    CodingUpdate(
        source="ADA CDT 2026",
        category="cdt_code",
        severity="important",
        title="D2391 Revised - Expanded Descriptor",
        description="D2391 descriptor expanded - no longer limited to restorations penetrating into dentin. "
        "Now covers the scope of former D1352 preventive resin restorations.",
        effective_date="2026-01-01",
        action_required="Update D2391 description and scenarios in knowledge base. AI should suggest D2391 for both traditional posterior composites and preventive resin restorations.",
        applied=True,
        found_date="2025-11-15",
    ),
    CodingUpdate(
        source="ADA CDT 2026",
        category="cdt_code",
        severity="important",
        title="D9230 Revised - Nitrous Oxide",
        description="D9230 nomenclature and descriptor revised. Now specifies administration of nitrous oxide "
        "as a single agent. Outdated language removed.",
        effective_date="2026-01-01",
        action_required="Update D9230 description in knowledge base.",
        applied=True,
        found_date="2025-11-15",
    ),
    CodingUpdate(
        source="ADA CDT 2026",
        category="cdt_code",
        severity="important",
        title="D5876 Revised - Metal Substructure",
        description="D5876 revised to clarify scope - used for documenting addition of metal substructure "
        "in removable complete denture for reinforcement.",
        effective_date="2026-01-01",
        action_required="Update D5876 description in knowledge base.",
        applied=True,
        found_date="2025-12-02",
    ),
    CodingUpdate(
        source="ADA CDT 2026",
        category="cdt_code",
        severity="informational",
        title="New Code D0418 - Saliva Testing",
        description="Point-of-care saliva sample analysis to identify markers for susceptibility to oral and systemic conditions.",
        effective_date="2026-01-01",
        action_required="Added to knowledge base.",
        applied=True,
        found_date="2025-09-15",
    ),
    CodingUpdate(
        source="ADA CDT 2026",
        category="cdt_code",
        severity="informational",
        title="New Code D0419 - Cracked Tooth Testing",
        description="Assessment of patient for cracked tooth using specialized testing methods.",
        effective_date="2026-01-01",
        action_required="Added to knowledge base.",
        applied=True,
        found_date="2025-09-15",
    ),
    CodingUpdate(
        source="ADA CDT 2026",
        category="cdt_code",
        severity="informational",
        title="New Codes D5115/D5125 - Backup Dentures",
        description="New codes for fabrication of backup dentures - D5115 maxillary, D5125 mandibular.",
        effective_date="2026-01-01",
        action_required="Added to knowledge base.",
        applied=True,
        found_date="2025-09-15",
    ),
    CodingUpdate(
        source="ADA CDT 2026",
        category="cdt_code",
        severity="informational",
        title="New Code D9947 - Occlusal Guard Cleaning",
        description="New code for cleaning and inspection of existing occlusal guard.",
        effective_date="2026-01-01",
        action_required="Added to knowledge base.",
        applied=True,
        found_date="2025-09-15",
    ),
    CodingUpdate(
        source="ADA CDT 2026",
        category="cdt_code",
        severity="breaking",
        title="COVID Vaccination Codes Deleted",
        description="D1701, D1702, D1703, D1704 deleted - AstraZeneca and Janssen vaccines no longer manufactured.",
        effective_date="2026-01-01",
        action_required="Removed from knowledge base. These codes will be rejected if submitted.",
        applied=True,
        found_date="2025-12-24",
    ),
]


class CodingUpdateAgent:
    """
    Agent that checks for and manages coding updates.

    Can be run in two modes:
    1. check_known_updates() - Reviews pre-loaded known updates
    2. check_for_updates() - Uses AI to analyze sources for new updates

    Update history is persisted to a JSON file.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._history: list[dict] = []
        self._load_history()

    def _load_history(self) -> None:
        """Load update history from disk."""
        try:
            with open(UPDATE_CHECK_FILE) as f:
                self._history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._history = []

    def _save_history(self) -> None:
        """Save update history to disk."""
        try:
            os.makedirs(os.path.dirname(UPDATE_CHECK_FILE), exist_ok=True)
            with open(UPDATE_CHECK_FILE, "w") as f:
                json.dump(self._history, f, indent=2)
        except OSError as e:
            logger.error("Failed to save update history: %s", e)

    def check_known_updates(self) -> UpdateCheckResult:
        """
        Check pre-loaded known updates (CDT 2026, etc.).
        Returns updates that haven't been applied yet.
        """
        now = datetime.now().isoformat()
        applied_titles = {
            h.get("title") for h in self._history if h.get("applied")
        }

        pending = []
        for update in CDT_2026_UPDATES:
            if update.title not in applied_titles:
                pending.append(update)

        result = UpdateCheckResult(
            checked_at=now,
            sources_checked=["CDT 2026 Known Updates"],
            updates_found=pending,
        )

        # Record the check
        self._history.append({
            "type": "check",
            "checked_at": now,
            "updates_found": len(pending),
        })
        self._save_history()

        return result

    def mark_applied(self, title: str) -> bool:
        """Mark an update as applied."""
        self._history.append({
            "type": "applied",
            "title": title,
            "applied": True,
            "applied_at": datetime.now().isoformat(),
        })
        self._save_history()
        return True

    def get_update_status(self) -> dict:
        """Get current update status summary."""
        applied_titles = {
            h.get("title") for h in self._history if h.get("applied")
        }

        all_updates = CDT_2026_UPDATES
        applied = [u for u in all_updates if u.title in applied_titles]
        pending = [u for u in all_updates if u.title not in applied_titles]

        return {
            "total_known_updates": len(all_updates),
            "applied": len(applied),
            "pending": len(pending),
            "pending_breaking": sum(
                1 for u in pending if u.severity == "breaking"
            ),
            "last_check": next(
                (
                    h["checked_at"]
                    for h in reversed(self._history)
                    if h.get("type") == "check"
                ),
                None,
            ),
            "sources": UPDATE_SOURCES,
            "pending_updates": [u.to_dict() for u in pending],
        }

    async def check_for_updates_ai(self, content: str, source: str) -> list[CodingUpdate]:
        """
        Use Claude to analyze content from an update source and extract
        any coding updates that affect our system.

        Args:
            content: Text content from a payer bulletin, ADA announcement, etc.
            source: Name of the source

        Returns:
            List of CodingUpdate objects found in the content
        """
        if not self._api_key:
            return []

        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self._api_key)

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=(
                "You are a dental coding update analyst. Analyze the following content "
                "and extract any changes that affect dental billing or coding. "
                "Return a JSON array of updates, each with: "
                "category (cdt_code/payer_rule/documentation/denial_code), "
                "severity (breaking/important/informational), "
                "title, description, effective_date, action_required. "
                "Return [] if no relevant updates found. Return ONLY valid JSON."
            ),
            messages=[{
                "role": "user",
                "content": f"Source: {source}\n\nContent:\n{content[:8000]}",
            }],
        )

        import re

        raw = response.content[0].text
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

        try:
            updates_data = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        updates = []
        now = datetime.now().strftime("%Y-%m-%d")
        for item in updates_data:
            updates.append(CodingUpdate(
                source=source,
                category=item.get("category", "informational"),
                severity=item.get("severity", "informational"),
                title=item.get("title", "Unknown update"),
                description=item.get("description", ""),
                effective_date=item.get("effective_date", ""),
                action_required=item.get("action_required", "Review required"),
                found_date=now,
            ))

        return updates

"""CDT Code reference database for AI-assisted dental coding.

Provides an in-memory repository of CDT codes with lookup, search, and
candidate-scoring capabilities used by the coding engine via RAG.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from buckteeth.knowledge.seed_data import SEED_CDT_CODES


@dataclass(frozen=True)
class CDTCode:
    """Reference data for a single CDT procedure code."""

    code: str
    description: str
    category: str
    subcategory: str
    common_scenarios: list[str] = field(default_factory=list)
    confused_with: list[str] = field(default_factory=list)
    bundling_notes: str = ""
    frequency_notes: str = ""
    narrative_required: bool = False
    common_denial_reasons: list[str] = field(default_factory=list)


class CDTCodeRepository:
    """In-memory reference database for CDT codes.

    Supports exact lookup, keyword search, category filtering, and
    scored candidate retrieval for a given procedure description.
    """

    def __init__(self) -> None:
        self._codes: dict[str, CDTCode] = {}
        self._load_seed_data()

    # ── public API ──────────────────────────────────────────────────────

    def lookup(self, code: str) -> CDTCode | None:
        """Return the CDTCode for an exact code string, or None."""
        return self._codes.get(code.upper().strip())

    def search(self, query: str, *, max_results: int = 10) -> list[CDTCode]:
        """Keyword search across descriptions and common scenarios.

        Returns up to *max_results* codes whose description or scenarios
        contain **all** query tokens (case-insensitive).
        """
        tokens = query.lower().split()
        if not tokens:
            return []

        results: list[CDTCode] = []
        for cdt in self._codes.values():
            searchable = " ".join(
                [cdt.description.lower(), cdt.code.lower()]
                + [s.lower() for s in cdt.common_scenarios]
            )
            if all(tok in searchable for tok in tokens):
                results.append(cdt)
            if len(results) >= max_results:
                break
        return results

    def search_by_category(self, category: str) -> list[CDTCode]:
        """Return all codes in the given category (case-insensitive)."""
        cat = category.lower().strip()
        return [c for c in self._codes.values() if c.category == cat]

    def get_candidates(
        self, procedure_description: str, *, max_results: int = 10
    ) -> list[CDTCode]:
        """Return scored candidate codes for a procedure description.

        Scoring is based on token overlap between the procedure description
        and each code's description + common scenarios.  Results are returned
        in descending score order, up to *max_results*.
        """
        tokens = set(procedure_description.lower().split())
        if not tokens:
            return []

        scored: list[tuple[float, CDTCode]] = []
        for cdt in self._codes.values():
            searchable_tokens = set(
                (
                    " ".join(
                        [cdt.description.lower()]
                        + [s.lower() for s in cdt.common_scenarios]
                    )
                ).split()
            )
            overlap = len(tokens & searchable_tokens)
            if overlap > 0:
                score = overlap / max(len(tokens), len(searchable_tokens))
                scored.append((score, cdt))

        scored.sort(key=lambda t: t[0], reverse=True)
        return [cdt for _, cdt in scored[:max_results]]

    # ── internals ───────────────────────────────────────────────────────

    def _load_seed_data(self) -> None:
        for row in SEED_CDT_CODES:
            cdt = CDTCode(
                code=row[0],
                description=row[1],
                category=row[2],
                subcategory=row[3],
                common_scenarios=list(row[4]),
                confused_with=list(row[5]),
                bundling_notes=row[6],
                frequency_notes=row[7],
                narrative_required=row[8],
                common_denial_reasons=list(row[9]),
            )
            self._codes[cdt.code] = cdt

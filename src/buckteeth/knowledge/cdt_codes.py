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
        self, procedure_description: str, *, max_results: int = 15
    ) -> list[CDTCode]:
        """Return scored candidate codes for a procedure description.

        Uses token overlap scoring weighted by match quality. Also does
        substring matching on key terms (crown, composite, extraction, etc.)
        to ensure important candidates aren't missed by tokenization.
        """
        query_lower = procedure_description.lower()
        tokens = set(query_lower.split())
        if not tokens:
            return []

        # Key term boosting — ensure category matches surface
        boosts: dict[str, list[str]] = {
            "crown": ["D2740", "D2750", "D2751", "D2752", "D2790", "D2791", "D2792", "D2950"],
            "porcelain": ["D2740", "D2750", "D2751"],
            "ceramic": ["D2740"],
            "pfm": ["D2750"],
            "core buildup": ["D2950", "D2952"],
            "buildup": ["D2950"],
            "root canal": ["D3310", "D3320", "D3330"],
            "endodontic": ["D3310", "D3320", "D3330"],
            "scaling": ["D4341", "D4342"],
            "root planing": ["D4341", "D4342"],
            "srp": ["D4341", "D4342"],
            "deep cleaning": ["D4341", "D4342"],
            "prophy": ["D1110", "D1120"],
            "cleaning": ["D1110", "D1120", "D4910"],
            "extraction": ["D7140", "D7210"],
            "surgical extract": ["D7210"],
            "impacted": ["D7220", "D7230", "D7240"],
            "composite": ["D2330", "D2331", "D2332", "D2391", "D2392", "D2393", "D2394"],
            "filling": ["D2140", "D2150", "D2160", "D2330", "D2391"],
            "amalgam": ["D2140", "D2150", "D2160", "D2161"],
            "denture": ["D5110", "D5120", "D5130", "D5140"],
            "implant": ["D6010", "D6056", "D6058", "D6059"],
            "bitewing": ["D0272", "D0274"],
            "periapical": ["D0220", "D0230"],
            "panoramic": ["D0330"],
            "veneer": ["D2960", "D2962"],
            "sealant": ["D1351"],
            "fluoride": ["D1206", "D1208"],
        }

        boosted_codes: set[str] = set()
        for term, codes in boosts.items():
            if term in query_lower:
                boosted_codes.update(codes)

        scored: list[tuple[float, CDTCode]] = []
        for cdt in self._codes.values():
            searchable = " ".join(
                [cdt.description.lower(), cdt.code.lower()]
                + [s.lower() for s in cdt.common_scenarios]
            )
            searchable_tokens = set(searchable.split())

            overlap = len(tokens & searchable_tokens)
            if overlap == 0 and cdt.code not in boosted_codes:
                continue

            # Score: overlap relative to query size (not code description size)
            score = overlap / len(tokens) if tokens else 0

            # Boost if code is in the boosted set
            if cdt.code in boosted_codes:
                score += 0.5

            # Boost substring matches in description
            for token in tokens:
                if len(token) >= 4 and token in searchable:
                    score += 0.1

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

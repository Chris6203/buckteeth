"""
Documentation Requirements Checker

Checks whether coded procedures have the required supporting documentation
(X-rays, radiographs, photos, narratives) that insurance companies expect.

Flags missing documentation BEFORE submission to prevent denials.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# CDT codes and their typical documentation requirements
# Based on common payer requirements across major dental insurers
DOCUMENTATION_REQUIREMENTS: dict[str, list[str]] = {
    # Crowns — almost always need pre-op radiograph
    "D2740": ["periapical_xray", "narrative"],
    "D2750": ["periapical_xray", "narrative"],
    "D2751": ["periapical_xray", "narrative"],
    "D2752": ["periapical_xray", "narrative"],
    "D2790": ["periapical_xray", "narrative"],
    "D2791": ["periapical_xray", "narrative"],
    "D2792": ["periapical_xray", "narrative"],
    "D2799": ["periapical_xray", "narrative"],
    # Core buildup — radiograph showing tooth structure
    "D2950": ["periapical_xray"],
    "D2952": ["periapical_xray"],
    # Endodontics — pre-op and working length radiographs
    "D3310": ["periapical_xray", "narrative"],
    "D3320": ["periapical_xray", "narrative"],
    "D3330": ["periapical_xray", "narrative"],
    "D3346": ["periapical_xray", "narrative"],
    "D3347": ["periapical_xray", "narrative"],
    "D3348": ["periapical_xray", "narrative"],
    # Periodontics — full mouth or BWX showing bone loss
    "D4341": ["bitewing_xray", "perio_charting"],
    "D4342": ["bitewing_xray", "perio_charting"],
    "D4355": ["bitewing_xray"],
    "D4910": ["bitewing_xray", "perio_charting"],
    # Oral surgery — radiograph of tooth/area
    "D7140": ["periapical_xray"],
    "D7210": ["periapical_xray", "narrative"],
    "D7220": ["periapical_xray", "narrative"],
    "D7230": ["periapical_xray", "narrative"],
    "D7240": ["periapical_xray", "panoramic_xray", "narrative"],
    "D7241": ["periapical_xray", "panoramic_xray", "narrative"],
    # Implants — radiograph + narrative
    "D6010": ["periapical_xray", "panoramic_xray", "narrative"],
    "D6012": ["periapical_xray", "panoramic_xray", "narrative"],
    "D6056": ["periapical_xray", "narrative"],
    "D6058": ["periapical_xray", "narrative"],
    "D6059": ["periapical_xray", "narrative"],
    # Prosthodontics
    "D5110": ["panoramic_xray", "narrative"],
    "D5120": ["panoramic_xray", "narrative"],
    "D5130": ["panoramic_xray", "narrative"],
    "D5140": ["panoramic_xray", "narrative"],
    # Large restorations — payers sometimes request radiograph for 3+ surfaces
    "D2160": ["bitewing_xray"],
    "D2161": ["bitewing_xray"],
    "D2332": ["bitewing_xray"],
    "D2335": ["bitewing_xray"],
    "D2393": ["bitewing_xray"],
    "D2394": ["bitewing_xray"],
    # Bridges / Fixed Prosthodontics — radiograph + narrative
    "D6210": ["periapical_xray", "narrative"],  # pontic
    "D6211": ["periapical_xray", "narrative"],
    "D6212": ["periapical_xray", "narrative"],
    "D6240": ["periapical_xray", "narrative"],
    "D6241": ["periapical_xray", "narrative"],
    "D6242": ["periapical_xray", "narrative"],
    "D6245": ["periapical_xray", "narrative"],
    "D6250": ["periapical_xray", "narrative"],
    "D6251": ["periapical_xray", "narrative"],
    "D6252": ["periapical_xray", "narrative"],
    "D6710": ["periapical_xray", "narrative"],  # retainer crown
    "D6720": ["periapical_xray", "narrative"],
    "D6740": ["periapical_xray", "narrative"],
    "D6750": ["periapical_xray", "narrative"],
    "D6751": ["periapical_xray", "narrative"],
    "D6752": ["periapical_xray", "narrative"],
    "D6780": ["periapical_xray", "narrative"],
    "D6790": ["periapical_xray", "narrative"],
    "D6791": ["periapical_xray", "narrative"],
    "D6792": ["periapical_xray", "narrative"],
    "D6794": ["periapical_xray", "narrative"],
    # Periodontal surgery — radiograph + perio charting + narrative
    "D4210": ["bitewing_xray", "perio_charting", "narrative"],
    "D4211": ["bitewing_xray", "perio_charting", "narrative"],
    "D4240": ["periapical_xray", "perio_charting", "narrative"],
    "D4241": ["periapical_xray", "perio_charting", "narrative"],
    "D4249": ["periapical_xray", "perio_charting", "narrative"],  # crown lengthening
    "D4260": ["periapical_xray", "perio_charting", "narrative"],  # osseous surgery
    "D4261": ["periapical_xray", "perio_charting", "narrative"],
    "D4263": ["periapical_xray", "narrative"],  # bone graft
    "D4264": ["periapical_xray", "narrative"],
    "D4270": ["periapical_xray", "perio_charting", "narrative"],  # soft tissue graft
    "D4273": ["periapical_xray", "perio_charting", "narrative"],
    "D4275": ["periapical_xray", "perio_charting", "narrative"],
    "D4276": ["periapical_xray", "perio_charting", "narrative"],
    "D4277": ["periapical_xray", "perio_charting", "narrative"],
    # Apicoectomy / endodontic surgery
    "D3410": ["periapical_xray", "narrative"],
    "D3421": ["periapical_xray", "narrative"],
    "D3425": ["periapical_xray", "narrative"],
    "D3426": ["periapical_xray", "narrative"],
    "D3430": ["periapical_xray", "narrative"],
    "D3450": ["periapical_xray", "narrative"],  # root amputation
    # Retreatment
    "D3346": ["periapical_xray", "narrative"],
    "D3347": ["periapical_xray", "narrative"],
    "D3348": ["periapical_xray", "narrative"],
    # Anterior composites (some payers request for 3+ surfaces)
    "D2335": ["bitewing_xray"],  # 4+ surfaces anterior
    # Veneers
    "D2960": ["intraoral_photo", "narrative"],
    "D2962": ["intraoral_photo", "narrative"],
    # Diagnostic — these ARE the documentation, no additional needed
    "D0120": [],
    "D0150": [],
    "D0210": [],
    "D0220": [],
    "D0230": [],
    "D0270": [],
    "D0272": [],
    "D0274": [],
    "D0330": [],
    # Preventive — typically no radiographs needed
    "D1110": [],
    "D1120": [],
    "D1206": [],
    "D1208": [],
    "D1351": [],
    "D1354": [],
    # Simple restorations — 1-2 surfaces usually don't need radiograph
    "D2140": [],
    "D2150": [],
    "D2330": [],
    "D2331": [],
    "D2391": [],
    "D2392": [],
}

DOC_TYPE_LABELS: dict[str, str] = {
    "periapical_xray": "Periapical X-ray",
    "bitewing_xray": "Bitewing X-rays",
    "panoramic_xray": "Panoramic X-ray",
    "perio_charting": "Periodontal charting (pocket depths)",
    "narrative": "Clinical narrative / medical necessity",
    "intraoral_photo": "Intraoral photograph",
}

DOC_TYPE_DESCRIPTIONS: dict[str, str] = {
    "periapical_xray": "A periapical radiograph of the affected tooth is typically required to show the extent of decay, infection, or structural damage.",
    "bitewing_xray": "Bitewing radiographs showing the interproximal surfaces and bone levels are needed to document the condition.",
    "panoramic_xray": "A panoramic radiograph showing the full arch is recommended for this procedure.",
    "perio_charting": "Periodontal charting with pocket depth measurements is required to document the severity of periodontal disease.",
    "narrative": "A clinical narrative explaining medical necessity may be requested by the payer.",
    "intraoral_photo": "An intraoral photograph documenting the clinical condition can strengthen the claim.",
}


@dataclass
class DocumentationAlert:
    """A single missing documentation alert."""

    cdt_code: str
    cdt_description: str
    missing_type: str  # Key from DOC_TYPE_LABELS
    label: str  # Human-readable label
    description: str  # Why it's needed
    severity: str  # "required" or "recommended"
    tooth_number: str | None = None


@dataclass
class DocumentationCheckResult:
    """Result of checking documentation completeness."""

    alerts: list[DocumentationAlert] = field(default_factory=list)
    complete: bool = True
    summary: str = ""

    @property
    def required_missing(self) -> list[DocumentationAlert]:
        return [a for a in self.alerts if a.severity == "required"]

    @property
    def recommended_missing(self) -> list[DocumentationAlert]:
        return [a for a in self.alerts if a.severity == "recommended"]

    def to_dict(self) -> dict:
        return {
            "alerts": [
                {
                    "cdt_code": a.cdt_code,
                    "cdt_description": a.cdt_description,
                    "missing_type": a.missing_type,
                    "label": a.label,
                    "description": a.description,
                    "severity": a.severity,
                    "tooth_number": a.tooth_number,
                }
                for a in self.alerts
            ],
            "complete": self.complete,
            "summary": self.summary,
        }


def check_documentation(
    coded_procedures: list[dict],
    has_images: bool = False,
    has_narrative: bool = False,
    has_perio_charting: bool = False,
) -> DocumentationCheckResult:
    """
    Check whether coded procedures have required supporting documentation.

    Args:
        coded_procedures: List of dicts with cdt_code, cdt_description,
                         tooth_number, surfaces
        has_images: Whether any images (X-rays, photos) were attached
        has_narrative: Whether clinical notes/narrative was provided
        has_perio_charting: Whether perio charting was included

    Returns:
        DocumentationCheckResult with any missing documentation alerts
    """
    alerts: list[DocumentationAlert] = []

    for proc in coded_procedures:
        code = proc.get("cdt_code", "")
        desc = proc.get("cdt_description", "")
        tooth = proc.get("tooth_number")

        requirements = DOCUMENTATION_REQUIREMENTS.get(code, [])

        for req in requirements:
            missing = False

            if req in ("periapical_xray", "bitewing_xray", "panoramic_xray", "intraoral_photo"):
                missing = not has_images
            elif req == "narrative":
                missing = not has_narrative
            elif req == "perio_charting":
                missing = not has_perio_charting

            if missing:
                # Radiographs for crowns/endo/surgery are required;
                # narratives are recommended
                severity = "required" if req.endswith("_xray") else "recommended"

                alerts.append(DocumentationAlert(
                    cdt_code=code,
                    cdt_description=desc,
                    missing_type=req,
                    label=DOC_TYPE_LABELS.get(req, req),
                    description=DOC_TYPE_DESCRIPTIONS.get(req, ""),
                    severity=severity,
                    tooth_number=tooth,
                ))

    # Deduplicate — if multiple procedures need same doc type, show once
    seen = set()
    deduped: list[DocumentationAlert] = []
    for alert in alerts:
        key = (alert.missing_type, alert.severity)
        if key not in seen:
            seen.add(key)
            deduped.append(alert)
        else:
            # Add the code to the description of the existing alert
            for existing in deduped:
                if existing.missing_type == alert.missing_type and existing.severity == alert.severity:
                    if alert.cdt_code not in existing.cdt_code:
                        existing.cdt_code += f", {alert.cdt_code}"
                    break

    complete = len([a for a in deduped if a.severity == "required"]) == 0

    if not deduped:
        summary = "All documentation requirements are met."
    elif complete:
        summary = f"{len(deduped)} recommended item(s) could strengthen your claim."
    else:
        required = len([a for a in deduped if a.severity == "required"])
        summary = f"{required} required document(s) missing — high denial risk without these."

    return DocumentationCheckResult(
        alerts=deduped,
        complete=complete,
        summary=summary,
    )

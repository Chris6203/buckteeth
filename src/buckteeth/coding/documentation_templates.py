"""
Smart Documentation Template Generator

Analyzes parsed procedures and generates specific documentation prompts
for the dentist. Instead of generic "attach an X-ray", it tells them
exactly what data and images they need for each specific procedure.

This runs AFTER note parsing but BEFORE coding, giving the dentist
a checklist of what to provide for maximum claim success.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DocumentationPrompt:
    """A specific piece of documentation the dentist should provide."""

    category: str  # "image", "measurement", "narrative_detail", "clinical_finding"
    label: str
    description: str
    required: bool
    for_procedure: str  # Which procedure this is for
    input_type: str  # "file", "text", "number", "select", "perio_chart"
    options: list[str] = field(default_factory=list)  # For select type


@dataclass
class DocumentationTemplate:
    """Complete documentation template for a set of procedures."""

    prompts: list[DocumentationPrompt] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "prompts": [
                {
                    "category": p.category,
                    "label": p.label,
                    "description": p.description,
                    "required": p.required,
                    "for_procedure": p.for_procedure,
                    "input_type": p.input_type,
                    "options": p.options,
                }
                for p in self.prompts
            ],
            "summary": self.summary,
            "required_count": sum(1 for p in self.prompts if p.required),
            "total_count": len(self.prompts),
        }


# Procedure-specific documentation requirements with detailed prompts
PROCEDURE_TEMPLATES: dict[str, list[DocumentationPrompt]] = {
    # ── Crowns ────────────────────────────────────────────────────────
    "crown": [
        DocumentationPrompt(
            category="image",
            label="Pre-operative periapical X-ray",
            description="Periapical radiograph showing the full tooth including apex. Must be taken within 12 months of the procedure date.",
            required=True,
            for_procedure="Crown",
            input_type="file",
        ),
        DocumentationPrompt(
            category="image",
            label="Intraoral photo of tooth",
            description="Photo showing the existing condition (decay, fracture, failing restoration) before preparation.",
            required=False,
            for_procedure="Crown",
            input_type="file",
        ),
        DocumentationPrompt(
            category="narrative_detail",
            label="Percentage of tooth structure compromised",
            description="Estimate what percentage of the tooth structure is compromised (e.g., '60% of tooth structure lost due to recurrent decay').",
            required=True,
            for_procedure="Crown",
            input_type="select",
            options=["25-40%", "40-50%", "50-60%", "60-75%", "75%+"],
        ),
        DocumentationPrompt(
            category="narrative_detail",
            label="Reason existing restoration failed",
            description="Why the current restoration is inadequate (e.g., 'Large MOD amalgam with recurrent decay at margins', 'Fractured cusp').",
            required=True,
            for_procedure="Crown",
            input_type="text",
        ),
        DocumentationPrompt(
            category="narrative_detail",
            label="Why alternatives are not viable",
            description="Why a direct restoration (filling) cannot adequately restore the tooth.",
            required=False,
            for_procedure="Crown",
            input_type="text",
        ),
    ],

    # ── SRP / Periodontics ────────────────────────────────────────────
    "srp": [
        DocumentationPrompt(
            category="image",
            label="Bitewing or periapical X-rays",
            description="Radiographs showing bone levels for the affected quadrant(s). Must show both arches and be taken within 12 months.",
            required=True,
            for_procedure="Scaling and Root Planing",
            input_type="file",
        ),
        DocumentationPrompt(
            category="measurement",
            label="Periodontal charting",
            description="Full periodontal chart with pocket depths, bleeding on probing, and clinical attachment loss. Pockets must be 4mm+ to justify SRP.",
            required=True,
            for_procedure="Scaling and Root Planing",
            input_type="perio_chart",
        ),
        DocumentationPrompt(
            category="clinical_finding",
            label="Periodontal diagnosis",
            description="AAP/EFP classification (e.g., 'Stage II, Grade B periodontitis') or at minimum 'moderate chronic periodontitis'.",
            required=True,
            for_procedure="Scaling and Root Planing",
            input_type="select",
            options=[
                "Stage I Periodontitis",
                "Stage II Periodontitis",
                "Stage III Periodontitis",
                "Stage IV Periodontitis",
                "Chronic Periodontitis - Localized",
                "Chronic Periodontitis - Generalized",
            ],
        ),
        DocumentationPrompt(
            category="measurement",
            label="Deepest pocket depth",
            description="The deepest probing depth found in the quadrant being treated.",
            required=True,
            for_procedure="Scaling and Root Planing",
            input_type="number",
        ),
        DocumentationPrompt(
            category="clinical_finding",
            label="Bleeding on probing",
            description="Note areas with bleeding on probing — this supports medical necessity.",
            required=False,
            for_procedure="Scaling and Root Planing",
            input_type="select",
            options=["Localized", "Generalized", "None"],
        ),
        DocumentationPrompt(
            category="clinical_finding",
            label="Bone loss pattern",
            description="Type of bone loss visible on radiographs.",
            required=False,
            for_procedure="Scaling and Root Planing",
            input_type="select",
            options=["Horizontal", "Vertical/Angular", "Combination", "Generalized"],
        ),
    ],

    # ── Root Canal / Endodontics ──────────────────────────────────────
    "endo": [
        DocumentationPrompt(
            category="image",
            label="Pre-operative periapical X-ray",
            description="Periapical radiograph showing the tooth with pathology (radiolucency, widened PDL space, etc.).",
            required=True,
            for_procedure="Root Canal",
            input_type="file",
        ),
        DocumentationPrompt(
            category="clinical_finding",
            label="Pulp diagnosis",
            description="AAE pulp diagnosis classification.",
            required=True,
            for_procedure="Root Canal",
            input_type="select",
            options=[
                "Irreversible Pulpitis",
                "Pulp Necrosis",
                "Previously Treated",
                "Previously Initiated Therapy",
            ],
        ),
        DocumentationPrompt(
            category="clinical_finding",
            label="Periapical diagnosis",
            description="AAE periapical diagnosis classification.",
            required=True,
            for_procedure="Root Canal",
            input_type="select",
            options=[
                "Normal Apical Tissues",
                "Symptomatic Apical Periodontitis",
                "Asymptomatic Apical Periodontitis",
                "Acute Apical Abscess",
                "Chronic Apical Abscess",
            ],
        ),
        DocumentationPrompt(
            category="clinical_finding",
            label="Symptoms",
            description="Patient symptoms that support the need for endodontic treatment.",
            required=False,
            for_procedure="Root Canal",
            input_type="text",
        ),
        DocumentationPrompt(
            category="clinical_finding",
            label="Pulp vitality test results",
            description="Results of cold test, EPT, or other vitality testing.",
            required=False,
            for_procedure="Root Canal",
            input_type="text",
        ),
    ],

    # ── Extractions ───────────────────────────────────────────────────
    "extraction": [
        DocumentationPrompt(
            category="image",
            label="Periapical X-ray of tooth",
            description="Periapical radiograph showing the tooth to be extracted and surrounding structures.",
            required=True,
            for_procedure="Extraction",
            input_type="file",
        ),
        DocumentationPrompt(
            category="narrative_detail",
            label="Reason for extraction",
            description="Clinical justification (e.g., 'Non-restorable due to extensive decay below CEJ', 'Severe periodontal disease with grade III mobility').",
            required=True,
            for_procedure="Extraction",
            input_type="text",
        ),
    ],

    # ── Surgical Extraction ───────────────────────────────────────────
    "surgical_extraction": [
        DocumentationPrompt(
            category="image",
            label="Periapical or panoramic X-ray",
            description="Radiograph showing tooth position, root anatomy, and proximity to vital structures.",
            required=True,
            for_procedure="Surgical Extraction",
            input_type="file",
        ),
        DocumentationPrompt(
            category="narrative_detail",
            label="Reason surgical approach was needed",
            description="Why a simple extraction was not possible (e.g., 'Impacted', 'Curved roots', 'Ankylosis', 'Crown completely destroyed requiring flap and bone removal').",
            required=True,
            for_procedure="Surgical Extraction",
            input_type="text",
        ),
    ],

    # ── Implants ──────────────────────────────────────────────────────
    "implant": [
        DocumentationPrompt(
            category="image",
            label="Panoramic X-ray",
            description="Panoramic radiograph showing available bone height and proximity to vital structures.",
            required=True,
            for_procedure="Implant",
            input_type="file",
        ),
        DocumentationPrompt(
            category="image",
            label="Periapical X-ray of implant site",
            description="Periapical radiograph of the edentulous area.",
            required=True,
            for_procedure="Implant",
            input_type="file",
        ),
        DocumentationPrompt(
            category="narrative_detail",
            label="Treatment plan narrative",
            description="Full treatment plan including why implant is preferred over alternatives (bridge, partial denture).",
            required=True,
            for_procedure="Implant",
            input_type="text",
        ),
        DocumentationPrompt(
            category="clinical_finding",
            label="Date of tooth loss",
            description="When the tooth was extracted — needed for missing tooth clause verification.",
            required=True,
            for_procedure="Implant",
            input_type="text",
        ),
    ],

    # ── Dentures / Prosthodontics ─────────────────────────────────────
    "denture": [
        DocumentationPrompt(
            category="image",
            label="Panoramic X-ray",
            description="Full panoramic radiograph showing remaining teeth and edentulous areas.",
            required=True,
            for_procedure="Denture",
            input_type="file",
        ),
        DocumentationPrompt(
            category="narrative_detail",
            label="Missing teeth and dates",
            description="List all missing teeth with approximate extraction dates — required for missing tooth clause.",
            required=True,
            for_procedure="Denture",
            input_type="text",
        ),
    ],

    # ── Large Restorations (3+ surfaces) ──────────────────────────────
    "large_restoration": [
        DocumentationPrompt(
            category="image",
            label="Bitewing or periapical X-ray",
            description="Radiograph showing the extent of decay or existing restoration failure.",
            required=False,
            for_procedure="Large Restoration",
            input_type="file",
        ),
        DocumentationPrompt(
            category="narrative_detail",
            label="Clinical findings",
            description="Describe the decay/damage and why multiple surfaces are involved.",
            required=False,
            for_procedure="Large Restoration",
            input_type="text",
        ),
    ],
}

# Map CDT code prefixes to template types
CODE_TO_TEMPLATE: dict[str, str] = {
    # Crowns
    "D2710": "crown", "D2712": "crown", "D2720": "crown", "D2721": "crown",
    "D2722": "crown", "D2740": "crown", "D2750": "crown", "D2751": "crown",
    "D2752": "crown", "D2780": "crown", "D2781": "crown", "D2782": "crown",
    "D2783": "crown", "D2790": "crown", "D2791": "crown", "D2792": "crown",
    "D2794": "crown", "D2799": "crown",
    # Core buildup (same docs as crown)
    "D2950": "crown", "D2952": "crown",
    # SRP / Perio
    "D4341": "srp", "D4342": "srp",
    "D4210": "srp", "D4211": "srp",
    "D4240": "srp", "D4241": "srp",
    "D4260": "srp", "D4261": "srp",
    "D4249": "srp",
    "D4910": "srp",
    # Endodontics
    "D3310": "endo", "D3320": "endo", "D3330": "endo",
    "D3346": "endo", "D3347": "endo", "D3348": "endo",
    # Simple extraction
    "D7140": "extraction",
    # Surgical extraction
    "D7210": "surgical_extraction", "D7220": "surgical_extraction",
    "D7230": "surgical_extraction", "D7240": "surgical_extraction",
    "D7241": "surgical_extraction",
    # Implants
    "D6010": "implant", "D6012": "implant", "D6013": "implant",
    "D6040": "implant", "D6050": "implant",
    "D6056": "implant", "D6057": "implant", "D6058": "implant",
    "D6059": "implant", "D6060": "implant",
    # Dentures
    "D5110": "denture", "D5120": "denture", "D5130": "denture",
    "D5140": "denture", "D5211": "denture", "D5212": "denture",
    "D5213": "denture", "D5214": "denture",
    # Large restorations (3+ surfaces)
    "D2160": "large_restoration", "D2161": "large_restoration",
    "D2332": "large_restoration", "D2335": "large_restoration",
    "D2393": "large_restoration", "D2394": "large_restoration",
}


def generate_documentation_template(
    procedures: list[dict],
) -> DocumentationTemplate:
    """
    Generate a documentation template based on parsed procedures.

    Called after note parsing to tell the dentist exactly what documentation
    they need to provide for each procedure.

    Args:
        procedures: List of dicts with description, tooth_numbers, surfaces,
                   quadrant, diagnosis, and optionally cdt_code

    Returns:
        DocumentationTemplate with specific prompts for each procedure
    """
    prompts: list[DocumentationPrompt] = []
    seen_templates: set[str] = set()

    for proc in procedures:
        cdt_code = proc.get("cdt_code", "")
        description = proc.get("description", "").lower()

        # Determine which template(s) apply
        template_keys: list[str] = []

        # Match by CDT code first
        if cdt_code and cdt_code in CODE_TO_TEMPLATE:
            template_keys.append(CODE_TO_TEMPLATE[cdt_code])

        # Match by description keywords if no code match
        if not template_keys:
            if any(w in description for w in ["crown", "crown prep"]):
                template_keys.append("crown")
            if any(w in description for w in ["srp", "scaling and root planing", "root planing", "deep cleaning", "perio"]):
                template_keys.append("srp")
            if any(w in description for w in ["root canal", "endodontic", "pulpectomy"]):
                template_keys.append("endo")
            if any(w in description for w in ["implant"]):
                template_keys.append("implant")
            if any(w in description for w in ["denture", "partial"]):
                template_keys.append("denture")
            if "surgical" in description and "extract" in description:
                template_keys.append("surgical_extraction")
            elif "extract" in description:
                template_keys.append("extraction")

            # Check for large restorations by surface count
            surfaces = proc.get("surfaces", [])
            if isinstance(surfaces, list) and len(surfaces) >= 3:
                if any(w in description for w in ["composite", "amalgam", "restoration", "filling"]):
                    template_keys.append("large_restoration")

        # Add prompts for each matched template (deduplicated)
        for key in template_keys:
            if key not in seen_templates:
                seen_templates.add(key)
                template_prompts = PROCEDURE_TEMPLATES.get(key, [])
                prompts.extend(template_prompts)

    # Generate summary
    required = sum(1 for p in prompts if p.required)
    if not prompts:
        summary = "No additional documentation needed for these procedures."
    elif required == 0:
        summary = f"{len(prompts)} optional documentation item(s) that could strengthen your claims."
    else:
        summary = f"{required} required item(s) and {len(prompts) - required} recommended item(s) to prevent denials."

    return DocumentationTemplate(prompts=prompts, summary=summary)

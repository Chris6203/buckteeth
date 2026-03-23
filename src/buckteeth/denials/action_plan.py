"""
Denial Action Plan Generator

Analyzes a denial and produces a specific, actionable plan for the dental
office to resolve it. Tells them exactly what documentation to gather,
what forms to fill out, and what steps to take — before they even
write the appeal letter.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ActionStep:
    """A single step the office needs to take."""
    order: int
    title: str
    description: str
    category: str  # "gather", "prepare", "submit", "follow_up"
    urgent: bool = False
    completed: bool = False


@dataclass
class DenialActionPlan:
    """Complete action plan for resolving a denial."""
    denial_type: str  # "missing_documentation", "frequency", "preauth", "medical_necessity", "other"
    summary: str
    steps: list[ActionStep] = field(default_factory=list)
    deadline_days: int | None = None
    deadline_note: str = ""
    what_went_wrong: str = ""
    how_to_prevent: str = ""

    def to_dict(self) -> dict:
        return {
            "denial_type": self.denial_type,
            "summary": self.summary,
            "what_went_wrong": self.what_went_wrong,
            "how_to_prevent": self.how_to_prevent,
            "deadline_days": self.deadline_days,
            "deadline_note": self.deadline_note,
            "steps": [
                {
                    "order": s.order,
                    "title": s.title,
                    "description": s.description,
                    "category": s.category,
                    "urgent": s.urgent,
                }
                for s in self.steps
            ],
            "total_steps": len(self.steps),
        }


# Denial reason code patterns → action plan templates
DENIAL_PATTERNS: dict[str, dict] = {
    # Missing documentation
    "N362": {
        "type": "missing_documentation",
        "what_went_wrong": "The claim was submitted without a tooth number, or the tooth number was invalid/missing from the claim form.",
        "how_to_prevent": "Always verify tooth numbers are included on the claim before submission. Use the pre-submission validator to catch this.",
        "steps": [
            ("gather", "Verify the correct tooth number", "Check your clinical notes and radiographs to confirm the exact tooth number for this procedure."),
            ("prepare", "Corrected claim form", "Prepare a corrected ADA claim form with the correct tooth number filled in."),
            ("submit", "Resubmit the corrected claim", "Submit the corrected claim to the payer. This is usually faster than a formal appeal since it's a clerical correction."),
        ],
    },
    "N382": {
        "type": "missing_documentation",
        "what_went_wrong": "The claim was submitted without tooth surface information, or the surfaces were invalid.",
        "how_to_prevent": "Always include surface codes (M, O, D, B, L) for restorative procedures. The pre-submission validator checks for this.",
        "steps": [
            ("gather", "Verify surfaces from clinical notes", "Check your charting to confirm which surfaces were restored (M, O, D, B, L, I, F)."),
            ("prepare", "Corrected claim form", "Prepare a corrected claim with the proper surface codes."),
            ("submit", "Resubmit the corrected claim", "Submit the corrected claim — this is a clerical fix, not a clinical dispute."),
        ],
    },
    # Pre-authorization missing
    "197": {
        "type": "preauth",
        "what_went_wrong": "The procedure required pre-authorization from the insurance company, but none was obtained before treatment. Many payers require predetermination for crowns, implants, orthodontics, and some periodontal procedures.",
        "how_to_prevent": "Before scheduling major procedures, check the patient's plan for pre-auth requirements. Our system flags these in the pre-submission validator. Submit a predetermination BEFORE treatment.",
        "steps": [
            ("gather", "Collect all clinical documentation", "Gather: pre-operative radiographs, clinical notes documenting medical necessity, intraoral photos if available, and the original treatment plan."),
            ("gather", "Get the patient's benefit information", "Pull the patient's plan details — some plans allow retroactive pre-auth within 30 days of service."),
            ("prepare", "Request retroactive pre-authorization", "Contact the payer to request retroactive pre-authorization. Many payers allow this if you can demonstrate the treatment was urgent or emergent. Document the clinical urgency."),
            ("prepare", "Write a medical necessity narrative", "Prepare a detailed narrative explaining why the procedure was medically necessary and why waiting for pre-auth was not clinically appropriate (if applicable)."),
            ("submit", "Submit the appeal with supporting documentation", "File a formal appeal including: the appeal letter, pre-op radiograph, clinical narrative, and retroactive pre-auth request. Send to the payer's appeal address."),
            ("follow_up", "Track the appeal", "Follow up in 30 days if no response. Document all communication. If denied again, consider a second-level appeal or state insurance commissioner complaint."),
        ],
    },
    # Frequency limitation
    "119": {
        "type": "frequency",
        "what_went_wrong": "The patient's annual benefit maximum has been reached, or the procedure exceeds the plan's frequency limitation (e.g., prophy only 2x/year, crown 1x/5 years per tooth).",
        "how_to_prevent": "Check the patient's remaining benefits BEFORE treatment. Verify the date of their last similar procedure. Our system checks frequency rules per payer in the pre-submission validator.",
        "steps": [
            ("gather", "Check the patient's benefit history", "Request a benefit breakdown from the payer showing: annual maximum, amount used, amount remaining, and dates of prior services for this CDT code."),
            ("gather", "Verify our records vs payer records", "Compare the payer's records with your own. Sometimes the payer has incorrect dates or has applied another provider's services to the same benefit."),
            ("prepare", "Determine if an exception applies", "Check if: (1) the prior service was by a different provider, (2) the tooth is different than what was previously treated, (3) clinical circumstances warrant an exception (e.g., trauma, failed restoration)."),
            ("prepare", "Write an exception request", "If circumstances warrant it, write a letter requesting an exception to the frequency limitation, citing the specific clinical reason (different tooth, failed treatment, changed condition)."),
            ("submit", "Submit the exception request or appeal", "File with supporting radiographs showing the current clinical need differs from the prior treatment."),
            ("follow_up", "Discuss with patient", "If the appeal is unsuccessful, discuss the out-of-pocket cost with the patient. Consider timing future treatment to fall within the next benefit period."),
        ],
    },
    # Medical necessity / not covered
    "50": {
        "type": "medical_necessity",
        "what_went_wrong": "The payer determined the procedure was not medically necessary based on the documentation submitted.",
        "how_to_prevent": "Always include a detailed clinical narrative explaining WHY the procedure was necessary. Include specific findings: measurements, radiographic evidence, symptoms. Use our documentation templates to ensure nothing is missed.",
        "steps": [
            ("gather", "Compile all clinical evidence", "Gather: radiographs (pre-op and post-op if available), periodontal charting, clinical photos, pulp vitality test results, and detailed clinical notes."),
            ("gather", "Review ADA/AAP guidelines", "Find the relevant ADA or AAP clinical practice guideline that supports this treatment for this diagnosis. Our system includes these in appeal letters."),
            ("prepare", "Write a detailed clinical narrative", "Prepare a narrative that includes: specific clinical findings, diagnosis, why this treatment was chosen over alternatives, and references to clinical guidelines."),
            ("prepare", "Get a peer review if needed", "For complex cases, consider getting a supporting letter from a specialist (periodontist, endodontist, oral surgeon) who reviewed the case."),
            ("submit", "File the appeal with all documentation", "Submit: appeal letter, all radiographs, clinical narrative, guideline references, and any specialist letters. Send to the payer's appeal address."),
            ("follow_up", "Track and escalate if needed", "If first appeal is denied, file a second-level appeal. If still denied, consider an external review or state insurance commissioner complaint."),
        ],
    },
    # Duplicate claim
    "18": {
        "type": "other",
        "what_went_wrong": "The payer flagged this as a duplicate of a previously submitted claim.",
        "how_to_prevent": "Check submission records before resubmitting. Use our idempotent submission gateway to prevent duplicates.",
        "steps": [
            ("gather", "Check your submission records", "Look up when the original claim was submitted and whether it was paid. Check your clearinghouse reports for the original tracking number."),
            ("prepare", "Determine if it's truly a duplicate", "If the original was paid, this is a true duplicate — no action needed. If the original was denied/lost, you need to resubmit as a corrected claim, not a new claim."),
            ("submit", "Resubmit correctly if needed", "If resubmission is needed, use claim frequency code 7 (replacement) or 8 (void) instead of 1 (original). Include the original claim number."),
        ],
    },
    # Time limit expired
    "29": {
        "type": "other",
        "what_went_wrong": "The claim was submitted after the payer's filing deadline. Most commercial payers require claims within 90-365 days of service.",
        "how_to_prevent": "Submit claims within 48 hours of service. Our system flags filing deadlines in the pre-submission validator.",
        "steps": [
            ("gather", "Document the reason for late filing", "Determine why the claim was late. Common acceptable reasons: waiting for other payer to process first (COB), claim was lost in clearinghouse transmission, patient provided insurance info late."),
            ("prepare", "Write a timely filing appeal", "Prepare a letter explaining the reason for late submission. Include proof of original submission attempt if the claim was lost."),
            ("submit", "Submit the appeal with proof", "Include: proof of timely filing attempt (clearinghouse receipt, fax confirmation), explanation letter, and the original claim."),
            ("follow_up", "Check state regulations", "Some states require payers to accept late claims under certain circumstances. Check your state's insurance regulations."),
        ],
    },
    # Charges exceed fee schedule
    "45": {
        "type": "other",
        "what_went_wrong": "The submitted fee exceeds the payer's maximum allowable amount (fee schedule). This is usually not an error — the payer simply pays their contracted rate.",
        "how_to_prevent": "This is normal — most payers pay their contracted rate, not your UCR fee. The difference may be written off (in-network) or billed to the patient (out-of-network).",
        "steps": [
            ("gather", "Review the EOB", "Check the Explanation of Benefits: what was the allowed amount? Was this an in-network or out-of-network adjustment?"),
            ("prepare", "Calculate patient responsibility", "If out-of-network, the patient may owe the difference between your fee and the payer's allowed amount. If in-network, you must write off the difference per your contract."),
            ("follow_up", "Bill the patient if appropriate", "Send the patient a statement for any remaining balance after insurance payment."),
        ],
    },
    # COB / another payer
    "22": {
        "type": "other",
        "what_went_wrong": "The payer believes another insurance should be primary. This happens with patients who have dual coverage.",
        "how_to_prevent": "Always verify coordination of benefits at each visit. Determine which plan is primary (birthday rule, employer rule, etc.).",
        "steps": [
            ("gather", "Verify primary vs secondary coverage", "Contact both payers to confirm which is primary. Use the birthday rule: the plan of the person whose birthday comes first in the calendar year is primary."),
            ("prepare", "Submit to the correct primary payer first", "If the claim was sent to the wrong payer as primary, submit to the correct primary payer first."),
            ("submit", "Then submit to secondary with primary's EOB", "After the primary payer processes the claim, submit to the secondary payer with a copy of the primary's EOB attached."),
        ],
    },
}

# Generic fallback for unknown denial codes
GENERIC_PLAN = {
    "type": "other",
    "what_went_wrong": "The claim was denied. Review the specific denial reason on the Explanation of Benefits (EOB) for details.",
    "how_to_prevent": "Use the pre-submission validator to catch common issues before submitting claims.",
    "steps": [
        ("gather", "Review the EOB carefully", "Read the Explanation of Benefits to understand exactly why the claim was denied. Note the denial reason code and description."),
        ("gather", "Collect supporting documentation", "Gather all relevant clinical records: notes, radiographs, photographs, and any prior correspondence with the payer."),
        ("prepare", "Contact the payer for clarification", "Call the payer's provider services line to understand what specific information they need to reconsider the claim."),
        ("prepare", "Prepare your response", "Based on what the payer needs, prepare the appropriate documentation and/or appeal letter."),
        ("submit", "Submit appeal or corrected claim", "Send the response to the payer's designated appeal address within their deadline."),
        ("follow_up", "Track and follow up", "Follow up in 30 days. Keep records of all communication."),
    ],
}


def generate_action_plan(
    denial_reason_code: str,
    denial_reason_description: str,
    payer_name: str,
    cdt_code: str = "",
    denied_amount: float = 0,
) -> DenialActionPlan:
    """
    Generate a specific action plan for resolving a denial.

    Args:
        denial_reason_code: CARC or payer-specific denial code
        denial_reason_description: Human-readable denial reason
        payer_name: Insurance company name
        cdt_code: CDT procedure code that was denied
        denied_amount: Dollar amount denied

    Returns:
        DenialActionPlan with specific steps to resolve
    """
    # Find matching pattern
    template = DENIAL_PATTERNS.get(denial_reason_code, None)

    # Try keyword matching on the description if no exact code match
    if template is None:
        desc_lower = denial_reason_description.lower()
        if "pre-auth" in desc_lower or "preauthorization" in desc_lower or "predetermination" in desc_lower:
            template = DENIAL_PATTERNS["197"]
        elif "charting" in desc_lower or "periodontal" in desc_lower:
            template = DENIAL_PATTERNS.get("N362", GENERIC_PLAN)
            # Override with perio-specific plan
            template = {
                "type": "missing_documentation",
                "what_went_wrong": "The SRP claim was denied because periodontal charting was not included. Insurance companies require full periodontal charting (pocket depths, bleeding on probing, clinical attachment levels) to justify scaling and root planing.",
                "how_to_prevent": "Always attach periodontal charting when submitting SRP claims (D4341/D4342). Our system flags this as a 90% denial risk if charting is missing.",
                "steps": [
                    ("gather", "Pull the periodontal charting", "Retrieve the full periodontal chart from the date of service. You need: 6-point probing depths for all teeth in the treated quadrant(s), bleeding on probing sites, and clinical attachment levels."),
                    ("gather", "Get the radiographs", "Pull the bitewing or periapical radiographs that show bone levels in the treated area. These must be taken within 12 months of the SRP date."),
                    ("prepare", "Write a clinical narrative", "Prepare a narrative that includes: periodontal diagnosis (Stage/Grade per AAP classification), specific pocket depths (e.g., '5-7mm pockets at teeth #2-5'), bleeding on probing findings, and radiographic bone loss description."),
                    ("prepare", "Complete a periodontal charting form", "If your charting isn't on a standard form, transfer the data to an ADA-compatible periodontal charting form that the payer can easily review."),
                    ("submit", "Submit the appeal with all documentation", "Send: appeal letter, complete periodontal charting, radiographs, and clinical narrative. Mark it as a response to the denial with the original claim number."),
                    ("follow_up", "Set a reminder for 30 days", "Follow up with the payer if you haven't received a response in 30 days."),
                ],
            }
        elif "frequency" in desc_lower or "maximum" in desc_lower or "benefit" in desc_lower:
            template = DENIAL_PATTERNS["119"]
        elif "duplicate" in desc_lower:
            template = DENIAL_PATTERNS["18"]
        elif "time limit" in desc_lower or "filing" in desc_lower or "timely" in desc_lower:
            template = DENIAL_PATTERNS["29"]
        elif "not medically necessary" in desc_lower or "not covered" in desc_lower:
            template = DENIAL_PATTERNS["50"]
        elif "coordination" in desc_lower or "other payer" in desc_lower:
            template = DENIAL_PATTERNS["22"]
        elif "fee schedule" in desc_lower or "exceeds" in desc_lower:
            template = DENIAL_PATTERNS["45"]

    if template is None:
        template = GENERIC_PLAN

    # Build steps
    steps = []
    for i, (category, title, description) in enumerate(template["steps"], 1):
        steps.append(ActionStep(
            order=i,
            title=title,
            description=description,
            category=category,
            urgent=i <= 2,
        ))

    # Determine deadline
    from buckteeth.edi.payer_directory import payer_directory
    deadline_days = 180  # default
    payer_results = payer_directory.search(payer_name)
    deadline_note = f"Most commercial payers allow 180 days to appeal."
    if payer_results:
        # Check PAYER_APPEAL_INFO for specific deadline
        from buckteeth.denials.appeal_generator import PAYER_APPEAL_INFO
        for key, info in PAYER_APPEAL_INFO.items():
            if key.lower() in payer_name.lower():
                deadline_days = info.get("appeal_deadline_days", 180)
                deadline_note = f"{payer_name} allows {deadline_days} days to file an appeal."
                break

    summary = f"${denied_amount:.2f} denied by {payer_name}"
    if cdt_code:
        summary += f" for {cdt_code}"

    return DenialActionPlan(
        denial_type=template["type"],
        summary=summary,
        steps=steps,
        deadline_days=deadline_days,
        deadline_note=deadline_note,
        what_went_wrong=template["what_went_wrong"],
        how_to_prevent=template["how_to_prevent"],
    )

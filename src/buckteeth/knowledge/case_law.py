from dataclasses import dataclass


@dataclass
class CaseLawEntry:
    citation: str
    title: str
    year: int
    state: str | None  # None = federal
    summary: str
    relevant_denial_codes: list[str]
    relevant_procedure_codes: list[str]
    ruling_summary: str
    key_principle: str


# Seed data: real legal principles, illustrative case names
SEED_CASE_LAW = [
    CaseLawEntry(
        citation="Hughes v. Blue Cross of California, 215 Cal.App.3d 832 (1989)",
        title="Hughes v. Blue Cross of California",
        year=1989, state="CA",
        summary="Insurer denied coverage claiming procedure was not medically necessary. Court found insurer acted in bad faith by relying on internal guidelines that contradicted accepted dental standards.",
        relevant_denial_codes=["CO-50", "CO-45"],
        relevant_procedure_codes=["D2740", "D2750", "D4341"],
        ruling_summary="Insurer cannot deny medically necessary procedures based solely on internal cost-containment guidelines that contradict accepted standards of dental practice.",
        key_principle="Medical necessity determined by treating provider, not insurer's internal guidelines",
    ),
    CaseLawEntry(
        citation="Hailey v. California Physicians' Service, 158 Cal.App.4th 452 (2007)",
        title="Hailey v. California Physicians' Service",
        year=2007, state="CA",
        summary="Patient denied coverage for procedure deemed experimental. Court ruled insurer must apply objective, evidence-based standards.",
        relevant_denial_codes=["CO-50", "CO-96"],
        relevant_procedure_codes=["D2740", "D2950"],
        ruling_summary="Insurers must use evidence-based, objective criteria when determining medical necessity, not arbitrary internal standards.",
        key_principle="Evidence-based determination required for medical necessity denials",
    ),
    CaseLawEntry(
        citation="McEvoy v. Group Health Cooperative, 570 N.W.2d 397 (1997)",
        title="McEvoy v. Group Health Cooperative",
        year=1997, state="WI",
        summary="Dental plan denied crown coverage citing frequency limitation. Court found limitation unreasonable when clinical evidence supported necessity.",
        relevant_denial_codes=["CO-119", "CO-45"],
        relevant_procedure_codes=["D2740", "D2750"],
        ruling_summary="Frequency limitations cannot override clinical necessity when documented by the treating dentist.",
        key_principle="Clinical necessity overrides arbitrary frequency limitations",
    ),
    CaseLawEntry(
        citation="ERISA Section 502(a)(1)(B), 29 U.S.C. § 1132",
        title="ERISA Federal Enforcement - Denial of Benefits",
        year=1974, state=None,
        summary="Federal law governing employee benefit plans. Requires full and fair review of denied claims. Plan administrators must provide specific reasons for denial and allow appeal.",
        relevant_denial_codes=["CO-45", "CO-50", "CO-96", "CO-119", "CO-4"],
        relevant_procedure_codes=[],
        ruling_summary="Plan administrators must provide adequate notice of denial reasons and opportunity for full and fair review.",
        key_principle="Claimants entitled to full and fair review of all denied claims under ERISA",
    ),
    CaseLawEntry(
        citation="Booton v. Lockheed Medical Benefit Plan, 110 F.3d 1461 (9th Cir. 1997)",
        title="Booton v. Lockheed Medical Benefit Plan",
        year=1997, state=None,
        summary="Court ruled that plan administrator abused discretion by denying dental benefits without adequate consideration of treating provider's recommendation.",
        relevant_denial_codes=["CO-50", "CO-4"],
        relevant_procedure_codes=["D3310", "D3320", "D3330"],
        ruling_summary="Plan administrators abuse discretion when they deny coverage without meaningfully considering the treating provider's clinical judgment.",
        key_principle="Treating provider's clinical judgment must be meaningfully considered",
    ),
    CaseLawEntry(
        citation="California Insurance Code § 10123.135",
        title="CA Timely Payment of Claims",
        year=2000, state="CA",
        summary="Requires insurers to pay undisputed claims within 30 working days. Failure triggers 15% annual interest penalty.",
        relevant_denial_codes=["CO-45", "CO-4", "CO-29"],
        relevant_procedure_codes=[],
        ruling_summary="Insurers must pay undisputed portions of claims within 30 working days or face interest penalties.",
        key_principle="Timely payment obligation with penalty interest for delays",
    ),
    CaseLawEntry(
        citation="ADA CDT Companion Guide - Bundling Position Statement",
        title="ADA Position on Improper Bundling",
        year=2023, state=None,
        summary="The ADA's official position that insurers improperly bundle distinct procedures, denying payment for services actually rendered. Each CDT code represents a separate procedure.",
        relevant_denial_codes=["CO-97", "CO-45"],
        relevant_procedure_codes=["D2950", "D2740", "D2750"],
        ruling_summary="Each CDT code represents a distinct procedure. Bundling separate procedures to deny payment violates ADA guidelines.",
        key_principle="Distinct CDT-coded procedures cannot be arbitrarily bundled to deny payment",
    ),
    CaseLawEntry(
        citation="National Association of Insurance Commissioners Model Act § 5",
        title="NAIC Unfair Claims Settlement Practices Model Act",
        year=1990, state=None,
        summary="Model regulation adopted by most states defining unfair claims practices including failing to affirm or deny coverage within reasonable time and not attempting in good faith to effectuate prompt settlement.",
        relevant_denial_codes=["CO-45", "CO-50", "CO-4", "CO-29"],
        relevant_procedure_codes=[],
        ruling_summary="Insurers must promptly investigate, affirm or deny claims, and attempt good faith settlement. Patterns of unfair practices are actionable.",
        key_principle="Good faith claims handling required; systematic unfair practices are actionable",
    ),
    CaseLawEntry(
        citation="Texas Insurance Code § 542.003 - Unfair Settlement Practices",
        title="Texas Prompt Payment of Claims Act",
        year=2003, state="TX",
        summary="Texas statute requiring insurers to acknowledge claims within 15 days, accept/deny within 45 days, and pay within 5 business days of acceptance. 18% penalty interest for violations.",
        relevant_denial_codes=["CO-4", "CO-29", "CO-45"],
        relevant_procedure_codes=[],
        ruling_summary="Strict timelines for claim processing with 18% penalty interest for non-compliance.",
        key_principle="Statutory timelines for claims processing with significant penalties",
    ),
    CaseLawEntry(
        citation="Moran v. Rush Prudential HMO, 536 U.S. 355 (2002)",
        title="Moran v. Rush Prudential HMO",
        year=2002, state=None,
        summary="Supreme Court upheld state laws requiring independent medical review of coverage denials, even for ERISA plans.",
        relevant_denial_codes=["CO-50", "CO-96"],
        relevant_procedure_codes=["D4341", "D4342", "D7210"],
        ruling_summary="State independent review requirements apply even to ERISA plans. Patients have right to independent review of medical necessity denials.",
        key_principle="Right to independent review of medical necessity denials",
    ),
]


class CaseLawRepository:
    def __init__(self):
        self._entries = SEED_CASE_LAW

    def search_by_denial_code(self, denial_code: str) -> list[CaseLawEntry]:
        return [e for e in self._entries if denial_code in e.relevant_denial_codes]

    def search(self, query: str) -> list[CaseLawEntry]:
        query_lower = query.lower()
        terms = query_lower.split()
        results = []
        for entry in self._entries:
            searchable = f"{entry.summary} {entry.ruling_summary} {entry.key_principle} {entry.title}".lower()
            if all(t in searchable for t in terms):
                results.append(entry)
        return results

    def search_by_state(self, state: str) -> list[CaseLawEntry]:
        return [e for e in self._entries
                if e.state == state or e.state is None]  # include federal

    def get_relevant_citations(
        self,
        denial_code: str,
        procedure_code: str | None = None,
        state: str | None = None,
    ) -> list[CaseLawEntry]:
        results = []
        for entry in self._entries:
            score = 0
            if denial_code in entry.relevant_denial_codes:
                score += 2
            if procedure_code and procedure_code in entry.relevant_procedure_codes:
                score += 1
            if state and (entry.state == state or entry.state is None):
                score += 1
            if score > 0:
                results.append((score, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results]

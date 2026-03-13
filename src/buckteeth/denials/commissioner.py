"""Claude-powered commissioner complaint letter generator for denied dental insurance claims.

Generates formal complaint letters to state insurance commissioners citing relevant
case law and regulatory references to challenge improper insurance claim denials.
"""

from __future__ import annotations

import json

import anthropic

from buckteeth.knowledge.case_law import CaseLawRepository
from buckteeth.denials.schemas import CommissionerLetterRequest, CommissionerLetterResponse

# Commissioner info for all 50 states + DC
STATE_COMMISSIONERS = {
    "AL": {"name": "Alabama Department of Insurance", "address": "201 Monroe St, Suite 502, Montgomery, AL 36104"},
    "AK": {"name": "Alaska Division of Insurance", "address": "550 W 7th Ave, Suite 1560, Anchorage, AK 99501"},
    "AZ": {"name": "Arizona Department of Insurance", "address": "100 N 15th Ave, Suite 261, Phoenix, AZ 85007"},
    "AR": {"name": "Arkansas Insurance Department", "address": "1 Commerce Way, Suite 102, Little Rock, AR 72202"},
    "CA": {"name": "California Department of Insurance", "address": "300 Capitol Mall, Suite 1700, Sacramento, CA 95814"},
    "CO": {"name": "Colorado Division of Insurance", "address": "1560 Broadway, Suite 850, Denver, CO 80202"},
    "CT": {"name": "Connecticut Insurance Department", "address": "153 Market St, Hartford, CT 06103"},
    "DE": {"name": "Delaware Department of Insurance", "address": "1351 W North St, Suite 101, Dover, DE 19904"},
    "FL": {"name": "Florida Office of Insurance Regulation", "address": "200 E Gaines St, Tallahassee, FL 32399"},
    "GA": {"name": "Georgia Office of Insurance", "address": "2 Martin Luther King Jr Dr SE, Suite 716W, Atlanta, GA 30334"},
    "HI": {"name": "Hawaii Insurance Division", "address": "335 Merchant St, Room 213, Honolulu, HI 96813"},
    "ID": {"name": "Idaho Department of Insurance", "address": "700 W State St, 3rd Floor, Boise, ID 83702"},
    "IL": {"name": "Illinois Department of Insurance", "address": "122 S Michigan Ave, 19th Floor, Chicago, IL 60603"},
    "IN": {"name": "Indiana Department of Insurance", "address": "311 W Washington St, Suite 103, Indianapolis, IN 46204"},
    "IA": {"name": "Iowa Insurance Division", "address": "Two Ruan Center, 601 Locust St, 4th Floor, Des Moines, IA 50309"},
    "KS": {"name": "Kansas Insurance Department", "address": "1300 SW Arrowhead Rd, Topeka, KS 66604"},
    "KY": {"name": "Kentucky Department of Insurance", "address": "500 Mero St, 2SE11, Frankfort, KY 40601"},
    "LA": {"name": "Louisiana Department of Insurance", "address": "1702 N 3rd St, Baton Rouge, LA 70802"},
    "ME": {"name": "Maine Bureau of Insurance", "address": "34 State House Station, Augusta, ME 04333"},
    "MD": {"name": "Maryland Insurance Administration", "address": "200 St Paul Pl, Suite 2700, Baltimore, MD 21202"},
    "MA": {"name": "Massachusetts Division of Insurance", "address": "1000 Washington St, Suite 810, Boston, MA 02118"},
    "MI": {"name": "Michigan Department of Insurance", "address": "530 W Allegan St, 7th Floor, Lansing, MI 48933"},
    "MN": {"name": "Minnesota Department of Commerce", "address": "85 7th Pl E, Suite 280, St Paul, MN 55101"},
    "MS": {"name": "Mississippi Insurance Department", "address": "1001 Woolfolk State Office Building, Jackson, MS 39201"},
    "MO": {"name": "Missouri Department of Commerce and Insurance", "address": "301 W High St, Room 530, Jefferson City, MO 65101"},
    "MT": {"name": "Montana Commissioner of Securities and Insurance", "address": "840 Helena Ave, Helena, MT 59601"},
    "NE": {"name": "Nebraska Department of Insurance", "address": "1135 M St, Suite 300, Lincoln, NE 68508"},
    "NV": {"name": "Nevada Division of Insurance", "address": "1818 E College Pkwy, Suite 103, Carson City, NV 89706"},
    "NH": {"name": "New Hampshire Insurance Department", "address": "21 S Fruit St, Suite 14, Concord, NH 03301"},
    "NJ": {"name": "New Jersey Department of Banking and Insurance", "address": "20 W State St, Trenton, NJ 08625"},
    "NM": {"name": "New Mexico Office of Superintendent of Insurance", "address": "1120 Paseo de Peralta, Room 428, Santa Fe, NM 87501"},
    "NY": {"name": "New York Department of Financial Services", "address": "One State St, New York, NY 10004"},
    "NC": {"name": "North Carolina Department of Insurance", "address": "1201 Mail Service Center, Raleigh, NC 27699"},
    "ND": {"name": "North Dakota Insurance Department", "address": "600 E Boulevard Ave, Bismarck, ND 58505"},
    "OH": {"name": "Ohio Department of Insurance", "address": "50 W Town St, Suite 300, Columbus, OH 43215"},
    "OK": {"name": "Oklahoma Insurance Department", "address": "400 NE 50th St, Oklahoma City, OK 73105"},
    "OR": {"name": "Oregon Division of Financial Regulation", "address": "350 Winter St NE, Room 410, Salem, OR 97301"},
    "PA": {"name": "Pennsylvania Insurance Department", "address": "1326 Strawberry Square, Harrisburg, PA 17120"},
    "RI": {"name": "Rhode Island Department of Business Regulation", "address": "1511 Pontiac Ave, Bldg 69-2, Cranston, RI 02920"},
    "SC": {"name": "South Carolina Department of Insurance", "address": "1201 Main St, Suite 1000, Columbia, SC 29201"},
    "SD": {"name": "South Dakota Division of Insurance", "address": "124 S Euclid Ave, 2nd Floor, Pierre, SD 57501"},
    "TN": {"name": "Tennessee Department of Commerce and Insurance", "address": "500 James Robertson Pkwy, Nashville, TN 37243"},
    "TX": {"name": "Texas Department of Insurance", "address": "1601 Congress Ave, Austin, TX 78701"},
    "UT": {"name": "Utah Insurance Department", "address": "4315 S 2700 W, Suite 2300, Taylorsville, UT 84129"},
    "VT": {"name": "Vermont Department of Financial Regulation", "address": "89 Main St, Montpelier, VT 05620"},
    "VA": {"name": "Virginia Bureau of Insurance", "address": "1300 E Main St, Richmond, VA 23219"},
    "WA": {"name": "Washington Office of Insurance Commissioner", "address": "302 Sid Snyder Ave SW, Suite 200, Olympia, WA 98504"},
    "WV": {"name": "West Virginia Offices of Insurance Commissioner", "address": "900 Pennsylvania Ave, Charleston, WV 25302"},
    "WI": {"name": "Wisconsin Office of Commissioner of Insurance", "address": "125 S Webster St, Madison, WI 53703"},
    "WY": {"name": "Wyoming Department of Insurance", "address": "106 E 6th Ave, Cheyenne, WY 82002"},
    "DC": {"name": "DC Department of Insurance", "address": "1050 First St NE, Suite 801, Washington, DC 20002"},
}

COMMISSIONER_SYSTEM_PROMPT = """\
You are a healthcare attorney specializing in dental insurance complaints. Your job is to write \
formal complaint letters to state insurance commissioners regarding improper claim denials.

Guidelines:
- Write a professional, formal complaint letter addressed to the state insurance commissioner.
- Reference specific case law, regulatory citations, and state insurance codes provided.
- Describe the denial, the clinical justification, and why the denial is improper.
- Request that the commissioner investigate the insurer's practices.
- Include the patient's and provider's information.
- Reference any prior appeal that was filed.
- Return your response as JSON with these fields:
  {"letter_text": "<full letter>", "commissioner_name": "<name>", "commissioner_address": "<address>", "case_law_citations": ["<list>"], "regulatory_citations": ["<list>"]}
- Return ONLY the JSON object, no other text.
"""


class CommissionerLetterGenerator:
    """Generates formal complaint letters to state insurance commissioners using Claude."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._case_law_repo = CaseLawRepository()

    def get_commissioner_info(self, state: str) -> dict:
        """Return commissioner name and address for the given state code."""
        return STATE_COMMISSIONERS.get(state, {
            "name": f"{state} Department of Insurance",
            "address": "Address not available",
        })

    async def generate(self, request: CommissionerLetterRequest) -> CommissionerLetterResponse:
        """Generate a formal complaint letter to the insurance commissioner."""
        # 1. Get relevant case law
        citations = self._case_law_repo.get_relevant_citations(
            denial_code=request.denial_reason_code,
            procedure_code=request.cdt_code,
            state=request.state,
        )
        commissioner = self.get_commissioner_info(request.state)

        # 2. Build prompt with case law context and commissioner info
        user_prompt = self._build_prompt(request, citations, commissioner)

        # 3. Call Claude
        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=COMMISSIONER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # 4. Parse response
        raw_text = response.content[0].text
        data = json.loads(raw_text)

        return CommissionerLetterResponse(
            letter_text=data["letter_text"],
            commissioner_name=data.get("commissioner_name", commissioner["name"]),
            commissioner_address=data.get("commissioner_address", commissioner["address"]),
            case_law_citations=data.get("case_law_citations", []),
            regulatory_citations=data.get("regulatory_citations", []),
        )

    @staticmethod
    def _build_prompt(request: CommissionerLetterRequest, citations, commissioner: dict) -> str:
        """Build the user prompt with denial details, commissioner info, and relevant case law."""
        case_law_text = ""
        for c in citations[:5]:  # top 5 most relevant
            case_law_text += f"\n- {c.citation}: {c.key_principle}"

        appeal_note = (
            "An appeal has already been filed and denied/ignored."
            if request.appeal_already_filed
            else "No formal appeal has been filed yet."
        )

        return f"""Commissioner Information:
- Name: {commissioner["name"]}
- Address: {commissioner["address"]}

Denial Details:
- Patient: {request.patient_name}
- Patient Address: {request.patient_address}
- Provider: {request.provider_name}
- Provider Address: {request.provider_address}
- Date of Service: {request.date_of_service}
- CDT Code: {request.cdt_code} - {request.procedure_description}
- Denial Reason: {request.denial_reason_code} - {request.denial_reason_description}
- Denied Amount: ${request.denied_amount:.2f}
- Insurance Company: {request.payer_name}
- State: {request.state}

Clinical Notes:
{request.clinical_notes}

Prior Appeal Status: {appeal_note}

Relevant Case Law and Regulations:
{case_law_text}

Generate a formal complaint letter to the insurance commissioner."""

import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=90.0,
    max_retries=0,
)


def run_sponsor_scout(
    *,
    event_name: str,
    event_address: str,
    radius_miles: float = 15,
    category: Optional[str] = None,
    max_results: int = 20,
) -> List[Dict[str, Any]]:

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    category_text = category or "any strong local sponsor category"

    prompt = f"""
Research real businesses that could sponsor this boxing event.

EVENT:
Name: {event_name}
Location: {event_address}
Search radius: approximately {radius_miles} miles
Category preference: {category_text}

Find up to {max_results} real businesses.

Prioritize businesses that show evidence of:
- local advertising or active marketing
- community sponsorships
- sports sponsorships
- nonprofit/community involvement
- event sponsorship
- strong audience fit for boxing, fitness, families, or local consumers
- enough business capacity to plausibly spend on sponsorship

IMPORTANT:
Do not claim a business has sponsored events unless you found evidence.
Do not invent marketing spend.
Distinguish verified evidence from inference.

Return ONLY valid JSON in this structure:

{{
  "results": [
    {{
      "business_name": "",
      "website": "",
      "city": "",
      "state": "",
      "industry": "",
      "why_good_fit": "",
      "marketing_evidence": [],
      "sponsorship_evidence": [],
      "source_urls": [],
      "marketing_activity_score": 0,
      "sponsorship_history_score": 0,
      "audience_fit_score": 0,
      "business_capacity_score": 0,
      "distance_score": 0,
      "relationship_score": 20,
      "discovery_score": 0,
      "marketing_propensity": "UNKNOWN",
      "verified_sponsorship_history": null,
      "lead_source": "OPENAI_WEB_SEARCH"
    }}
  ]
}}
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        tools=[{"type": "web_search"}],
        include=["web_search_call.action.sources"],
        input=prompt,
    )

    raw = response.output_text.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "", 1)
        raw = raw.replace("```", "").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"OpenAI Sponsor Scout returned invalid JSON: {raw[:500]}"
        ) from exc

    results = data.get("results", [])

    if not isinstance(results, list):
        raise RuntimeError("Sponsor Scout response did not contain a results list.")

    results.sort(
        key=lambda item: item.get("discovery_score", 0),
        reverse=True,
    )

    return results

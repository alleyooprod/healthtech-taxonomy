"""Waterfall company enrichment: multi-step pipeline to fill missing fields."""
import json
import time

from core.llm import run_cli


# Fields that can be enriched
ENRICHABLE_FIELDS = [
    "what", "target", "products", "funding", "geography", "tam",
    "employee_range", "founded_year", "funding_stage", "total_funding_usd",
    "hq_city", "hq_country", "linkedin_url", "business_model",
    "company_stage", "primary_focus", "tags",
]


def identify_missing_fields(company):
    """Return list of fields that are empty or None."""
    missing = []
    for f in ENRICHABLE_FIELDS:
        val = company.get(f)
        if val is None or val == "" or val == []:
            missing.append(f)
    return missing


def run_enrichment(company, fields_to_fill=None, model="sonnet"):
    """Run 3-step waterfall enrichment for a single company.

    Steps:
        1. Extract from existing raw_research
        2. Web search for missing data
        3. Targeted follow-up for remaining gaps

    Returns dict of enriched field values.
    """
    name = company.get("name", "Unknown")
    url = company.get("url", "")
    fields_to_fill = fields_to_fill or identify_missing_fields(company)

    if not fields_to_fill:
        return {"enriched_fields": {}, "steps_run": 0}

    enriched = {}
    remaining = list(fields_to_fill)

    # Step 1: Extract from existing research text
    raw = company.get("raw_research", "")
    if raw and remaining:
        prompt = f"""Extract the following fields from this company research text.
Company: {name} ({url})

Research text:
{raw[:3000]}

Fields to extract: {', '.join(remaining)}

Return JSON only with field names as keys. Use null for fields you cannot determine.
For 'tags', return a JSON array of strings. For numeric fields, return numbers.
"""
        try:
            resp = run_cli(prompt, model, timeout=60)
            result = resp.get("structured_output") or resp.get("result", "")
            if isinstance(result, str):
                # Try to extract JSON from response
                start = result.find("{")
                end = result.rfind("}") + 1
                if start >= 0 and end > start:
                    result = json.loads(result[start:end])
            if isinstance(result, dict):
                for k, v in result.items():
                    if k in remaining and v is not None and v != "" and v != []:
                        enriched[k] = v
                        remaining.remove(k)
        except Exception:
            pass

    if not remaining:
        return {"enriched_fields": enriched, "steps_run": 1}

    # Step 2: Web search for missing data
    prompt = f"""Research the company "{name}" ({url}) and find the following information:
{', '.join(remaining)}

Search the web for this company's website, Crunchbase profile, LinkedIn page, and news articles.
Return JSON only with field names as keys. Use null for fields you cannot find.
For 'tags', return a JSON array of relevant industry tags.
For numeric fields like total_funding_usd and founded_year, return numbers.
"""
    try:
        resp = run_cli(prompt, model, timeout=120, tools="WebSearch,WebFetch")
        result = resp.get("structured_output") or resp.get("result", "")
        if isinstance(result, str):
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(result[start:end])
        if isinstance(result, dict):
            for k, v in result.items():
                if k in remaining and v is not None and v != "" and v != []:
                    enriched[k] = v
                    remaining.remove(k)
    except Exception:
        pass

    if not remaining:
        return {"enriched_fields": enriched, "steps_run": 2}

    # Step 3: Targeted follow-up for stubborn gaps
    prompt = f"""I need specific information about "{name}" ({url}).
Please search harder for these specific fields: {', '.join(remaining)}

Try searching for:
- "{name} funding crunchbase" for funding data
- "{name} linkedin" for employee and location data
- "{name} founded" for founding year
- The company website for product and business model details

Return JSON only with field names as keys. Use null if truly unavailable.
"""
    try:
        resp = run_cli(prompt, model, timeout=120, tools="WebSearch,WebFetch")
        result = resp.get("structured_output") or resp.get("result", "")
        if isinstance(result, str):
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(result[start:end])
        if isinstance(result, dict):
            for k, v in result.items():
                if k in remaining and v is not None and v != "" and v != []:
                    enriched[k] = v
                    remaining.remove(k)
    except Exception:
        pass

    return {"enriched_fields": enriched, "steps_run": 3}

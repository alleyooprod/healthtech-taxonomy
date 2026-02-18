"""Per-company deep research using the LLM layer."""
import json
import logging

from config import PROMPTS_DIR, RESEARCH_TIMEOUT
from core.llm import run_cli

logger = logging.getLogger(__name__)

_RESEARCH_REQUIRED_FIELDS = {"name", "url"}


def _validate_research(data, url):
    """Validate LLM research output has required fields and sane values."""
    if not isinstance(data, dict):
        raise ValueError(f"Research output for {url} is not a dict")
    missing = _RESEARCH_REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise ValueError(f"Research output for {url} missing required fields: {missing}")
    if "confidence_score" in data and data["confidence_score"] is not None:
        try:
            data["confidence_score"] = max(0.0, min(1.0, float(data["confidence_score"])))
        except (ValueError, TypeError):
            data["confidence_score"] = None
    return data


def research_company(url, model="claude-opus-4-6"):
    """Run deep research on a single company URL.

    Returns a dict with all extracted company fields.
    Raises RuntimeError on failure.
    """
    prompt_template = (PROMPTS_DIR / "research.txt").read_text()
    prompt = prompt_template.format(url=url)
    schema = (PROMPTS_DIR / "schemas" / "company_research.json").read_text()

    response = run_cli(prompt, model, timeout=RESEARCH_TIMEOUT,
                       tools="WebSearch,WebFetch", json_schema=schema)

    structured = response.get("structured_output")
    if not structured:
        raw = response.get("result", "")
        try:
            structured = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raise ValueError(
                f"No structured output for {url}. Raw result: {raw[:300]}"
            )

    structured = _validate_research(structured, url)

    # Attach cost metadata
    structured["_cost_usd"] = response.get("cost_usd", 0)
    structured["_duration_ms"] = response.get("duration_ms", 0)
    structured["_model"] = model

    return structured


def research_company_with_sources(source_urls, existing_research, model="claude-opus-4-6"):
    """Re-research a company using additional source URLs.

    Sends existing research + new URLs to Claude for enrichment.
    Returns updated research dict with improved data and confidence.
    """
    prompt_template = (PROMPTS_DIR / "re_research.txt").read_text()

    # Clean internal metadata from existing research
    clean_existing = {k: v for k, v in existing_research.items() if not k.startswith("_")}

    prompt = prompt_template.format(
        existing_research=json.dumps(clean_existing, indent=2),
        source_urls="\n".join(f"- {url}" for url in source_urls),
    )

    schema = (PROMPTS_DIR / "schemas" / "company_research.json").read_text()

    response = run_cli(prompt, model, timeout=RESEARCH_TIMEOUT,
                       tools="WebSearch,WebFetch", json_schema=schema)

    structured = response.get("structured_output")
    if not structured:
        raw = response.get("result", "")
        try:
            structured = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raise ValueError(f"No structured re-research output. Raw: {raw[:300]}")

    structured["_cost_usd"] = response.get("cost_usd", 0)
    structured["_duration_ms"] = response.get("duration_ms", 0)
    structured["_model"] = model

    return structured

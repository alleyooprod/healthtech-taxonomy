"""Classify a company into the taxonomy using the LLM layer."""
import json

from config import PROMPTS_DIR, CLASSIFY_TIMEOUT
from core.llm import run_cli


def classify_company(company_data, taxonomy_tree, model="claude-opus-4-6"):
    """Classify a company into the taxonomy.

    Args:
        company_data: Dict with company research fields.
        taxonomy_tree: String representation of current taxonomy with counts.
        model: Claude model to use.

    Returns dict with category, subcategory, is_new_category, confidence, reasoning.
    """
    prompt_template = (PROMPTS_DIR / "classify.txt").read_text()

    # Strip internal metadata from company data before sending
    clean_data = {k: v for k, v in company_data.items() if not k.startswith("_")}
    company_json = json.dumps(clean_data, indent=2)

    prompt = prompt_template.format(
        company_json=company_json,
        taxonomy_tree=taxonomy_tree,
    )

    schema = (PROMPTS_DIR / "schemas" / "company_classification.json").read_text()

    response = run_cli(prompt, model, timeout=CLASSIFY_TIMEOUT,
                       json_schema=schema)

    structured = response.get("structured_output")
    if not structured:
        raw = response.get("result", "")
        try:
            structured = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raise ValueError(f"No structured classification output. Raw: {raw[:300]}")

    # Validate required fields
    if not isinstance(structured, dict):
        raise ValueError("Classification output is not a dict")
    if "confidence" in structured and structured["confidence"] is not None:
        try:
            structured["confidence"] = max(0.0, min(1.0, float(structured["confidence"])))
        except (ValueError, TypeError):
            structured["confidence"] = None

    return structured


def build_taxonomy_tree_string(db, project_id=None):
    """Build a human-readable taxonomy tree string from the database."""
    stats = db.get_category_stats(project_id=project_id)
    lines = []
    # Top-level categories (no parent)
    top_level = [s for s in stats if s["parent_id"] is None]
    subcategories = [s for s in stats if s["parent_id"] is not None]

    for cat in sorted(top_level, key=lambda x: x["name"]):
        lines.append(f"- {cat['name']} ({cat['company_count']} companies)")
        # Find subcategories
        subs = [s for s in subcategories if s["parent_id"] == cat["id"]]
        for sub in sorted(subs, key=lambda x: x["name"]):
            lines.append(f"  - {sub['name']} ({sub['company_count']} companies)")

    return "\n".join(lines)

"""AI features API: discover, find-similar, chat, market reports."""
import json
import re
import subprocess

from flask import Blueprint, current_app, jsonify, request

from config import DATA_DIR, DEFAULT_MODEL, MODEL_CHOICES
from core.git_sync import sync_to_git_async
from core.llm import run_cli
from storage.db import Database
from web.async_jobs import start_async_job, write_result, poll_result

ai_bp = Blueprint("ai", __name__)


def _sanitize_for_prompt(text, max_length=500):
    """Sanitize user input before interpolating into AI prompts.
    Strips control chars, prompt injection markers, and truncates."""
    if not text:
        return ""
    # Strip non-printable/control characters
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    sanitized = sanitized.replace("```", "").replace("---", "")
    # Case-insensitive removal of prompt injection markers
    injection_patterns = [
        r'(?i)\bsystem\s*:', r'(?i)\bassistant\s*:', r'(?i)\bhuman\s*:',
        r'(?i)\buser\s*:', r'(?i)\binstruction\s*:',
        r'(?i)ignore\s+(previous|above|all)', r'(?i)disregard',
        r'(?i)forget\s+(everything|previous|all|above)',
        r'(?i)you\s+are\s+now', r'(?i)new\s+instructions?\s*:',
        r'(?i)override\s+(previous|all|system)',
    ]
    for pattern in injection_patterns:
        sanitized = re.sub(pattern, '', sanitized)
    sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)
    return sanitized[:max_length].strip()


# --- Models ---

@ai_bp.route("/api/ai/models")
def ai_models():
    return jsonify({
        "models": MODEL_CHOICES,
        "providers": {
            "claude": {
                "models": {k: v for k, v in MODEL_CHOICES.items()
                           if not v.startswith("gemini")},
                "label": "Claude (Anthropic)",
            },
            "gemini": {
                "models": {k: v for k, v in MODEL_CHOICES.items()
                           if v.startswith("gemini")},
                "label": "Gemini (Google)",
            },
        },
    })


# --- Discover ---

def _run_discover(job_id, query, model):
    safe_query = _sanitize_for_prompt(query)
    prompt = f"""You are a market research assistant. The user is looking for companies in this space:

"{safe_query}"

Search the web and return a JSON array of 5-10 company objects, each with:
- "name": company name
- "url": company website URL (must be real, working URLs)
- "description": 1-sentence description of what they do

Only return the JSON array, nothing else. Focus on real, existing companies."""

    try:
        response = run_cli(prompt, model, timeout=120)
        text = response.get("result", "")
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            companies = json.loads(match.group())
            result = {"status": "complete", "companies": companies}
        else:
            result = {"status": "complete", "companies": [], "raw": text}
    except subprocess.TimeoutExpired:
        result = {"status": "error", "error": "Discovery timed out. Try a simpler query."}
    except json.JSONDecodeError:
        result = {"status": "error", "error": "Failed to parse AI response."}
    except Exception as e:
        result = {"status": "error", "error": str(e)[:200]}

    write_result("discover", job_id, result)


@ai_bp.route("/api/ai/discover", methods=["POST"])
def ai_discover():
    data = request.json
    query = data.get("query", "").strip()
    model = data.get("model", DEFAULT_MODEL)
    if not query:
        return jsonify({"error": "Query is required"}), 400

    discover_id = start_async_job("discover", _run_discover, query, model)
    return jsonify({"discover_id": discover_id})


@ai_bp.route("/api/ai/discover/<discover_id>")
def get_discover_status(discover_id):
    return jsonify(poll_result("discover", discover_id))


# --- Find Similar ---

def _run_find_similar(job_id, company, model):
    safe_name = _sanitize_for_prompt(company['name'], 100)
    safe_what = _sanitize_for_prompt(company.get('what', 'N/A'), 200)
    safe_target = _sanitize_for_prompt(company.get('target', 'N/A'), 200)

    prompt = f"""You are a market research assistant. Given this company:

Name: {safe_name}
URL: {company['url']}
What they do: {safe_what}
Target: {safe_target}
Category: {company.get('category_name', 'N/A')}

Search the web and find 5 similar or competing companies. Return a JSON array with:
- "name": company name
- "url": company website URL
- "description": 1-sentence description
- "similarity": brief explanation of why it's similar

Only return the JSON array, nothing else."""

    try:
        response = run_cli(prompt, model, timeout=120)
        text = response.get("result", "")
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            companies = json.loads(match.group())
            result = {"status": "complete", "companies": companies}
        else:
            result = {"status": "complete", "companies": [], "raw": text}
    except subprocess.TimeoutExpired:
        result = {"status": "error", "error": "Search timed out. Please try again."}
    except json.JSONDecodeError:
        result = {"status": "error", "error": "Failed to parse AI response."}
    except Exception as e:
        result = {"status": "error", "error": str(e)[:200]}

    write_result("similar", job_id, result)


@ai_bp.route("/api/ai/find-similar", methods=["POST"])
def ai_find_similar():
    db = current_app.db
    data = request.json
    company_id = data.get("company_id")
    model = data.get("model", DEFAULT_MODEL)
    if not company_id:
        return jsonify({"error": "company_id is required"}), 400

    company = db.get_company(company_id)
    if not company:
        return jsonify({"error": "Company not found"}), 404

    similar_id = start_async_job("similar", _run_find_similar, company, model)
    return jsonify({"similar_id": similar_id})


@ai_bp.route("/api/ai/find-similar/<similar_id>")
def get_similar_status(similar_id):
    return jsonify(poll_result("similar", similar_id))


# --- Chat ---

@ai_bp.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    db = current_app.db
    data = request.json
    question = data.get("question", "").strip()
    project_id = data.get("project_id")
    model = data.get("model", "claude-haiku-4-5-20251001")
    if not question:
        return jsonify({"error": "Question is required"}), 400

    companies = db.get_companies(project_id=project_id, limit=200)
    stats = db.get_stats(project_id=project_id)
    categories = db.get_category_stats(project_id=project_id)

    context = f"""You have access to a taxonomy database with {stats['total_companies']} companies across {stats['total_categories']} categories.

Categories: {', '.join(c['name'] + f' ({c["company_count"]})' for c in categories if not c.get('parent_id'))}

Companies (name | category | what they do | tags):
"""
    for c in companies[:100]:
        tags = ', '.join(c.get('tags', []))
        context += f"- {c['name']} | {c.get('category_name', 'N/A')} | {c.get('what', 'N/A')[:80]} | {tags}\n"

    prompt = f"""{context}

Answer this question using ONLY the data above. Be extremely brief and data-focused.
Rules:
- Use bullet points, not paragraphs
- Include specific company names, numbers, and categories
- Maximum 5-8 bullet points
- No preamble or pleasantries

Question: {_sanitize_for_prompt(question)}"""

    try:
        response = run_cli(prompt, model, timeout=60)
        answer = response.get("result", "")
        return jsonify({"answer": answer})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Request timed out. Try a simpler question."}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse AI response."}), 500
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


# --- Market Report ---

def _run_market_report(job_id, category_name, project_id, model):
    report_db = Database()
    companies = report_db.get_companies(project_id=project_id, limit=200)
    cat_companies = [c for c in companies if c.get('category_name') == category_name]

    company_summaries = "\n".join([
        f"### {c['name']}\n"
        f"- URL: {c.get('url','')}\n"
        f"- Description: {c.get('what','N/A')}\n"
        f"- Target Market: {c.get('target','N/A')}\n"
        f"- Products: {c.get('products','N/A')}\n"
        f"- Funding: {c.get('funding','N/A')}\n"
        f"- Funding Stage: {c.get('funding_stage','N/A')}\n"
        f"- Total Raised: {c.get('total_funding_usd','N/A')}\n"
        f"- Geography: {c.get('geography','N/A')}\n"
        f"- HQ: {c.get('hq_city','')}, {c.get('hq_country','')}\n"
        f"- Employees: {c.get('employee_range','N/A')}\n"
        f"- Founded: {c.get('founded_year','N/A')}\n"
        f"- TAM: {c.get('tam','N/A')}\n"
        f"- Tags: {', '.join(c.get('tags',[]))}\n"
        for c in cat_companies
    ])

    prompt = f"""You are a senior market analyst at a tier-1 research firm (similar to Gartner, IDC, or Mintel). Generate a rigorous, data-driven market intelligence briefing for the "{category_name}" category.

COMPANY DATA (from our proprietary database):
{company_summaries}

INSTRUCTIONS:
1. First, analyze the company data provided above
2. Then, use WebSearch to validate and enrich your findings:
   - Search for recent market reports, funding announcements, or industry trends related to this category
   - Search for market size data (TAM/SAM/SOM) for this sector
   - Search for any recent news about the key companies listed
3. Synthesize everything into a structured analyst briefing

REQUIRED FORMAT (Markdown):

# {category_name}: Market Intelligence Briefing

## Executive Summary
[2-3 sentence overview. Include estimated market size if found via search.]

## Market Landscape
[Include a mermaid quadrant chart showing competitive positioning]

```mermaid
quadrantChart
    title Competitive Positioning
    x-axis Low Market Focus --> High Market Focus
    y-axis Early Stage --> Mature
    [Position companies based on your analysis]
```

## Key Players & Competitive Analysis
[For each significant company: what they do, differentiation, funding stage, and competitive position. Use a markdown table.]

| Company | Focus | Funding Stage | Differentiation |
|---------|-------|--------------|-----------------|
...

## Market Dynamics
### Tailwinds
[3-4 factors driving growth, with citations]

### Headwinds
[2-3 challenges or risks, with citations]

## Funding & Investment Patterns
[Aggregate funding analysis. Include total capital deployed, average round size, most active investors if findable]

## Outlook & Implications
[Forward-looking analysis with points AND counterpoints. What does this mean for insurers/investors/operators?]

## Sources & Citations
[List all web sources consulted with URLs]

CONSTRAINTS:
- Total length: 1500-2000 words (approximately 2 A4 pages)
- Every factual claim from web search must include a citation [Source Name](URL)
- Be specific: use company names, dollar amounts, dates
- Maintain analytical objectivity - present both bull and bear cases
- If you cannot verify a claim via web search, explicitly note it as "per company self-reporting"
"""

    try:
        response = run_cli(
            prompt, model, timeout=300,
            tools="WebSearch,WebFetch",
        )
        report = response.get("result", "")
        result_data = {"status": "complete", "report": report,
                       "category": category_name,
                       "company_count": len(cat_companies)}
    except subprocess.TimeoutExpired:
        result_data = {"status": "error",
                       "error": "Report generation timed out after 5 minutes. Try a smaller category or a faster model."}
    except json.JSONDecodeError:
        result_data = {"status": "error",
                       "error": "Failed to parse AI response. Please try again."}
    except Exception as e:
        result_data = {"status": "error", "error": str(e)[:300]}

    write_result("report", job_id, result_data)

    if result_data.get("status") == "complete":
        report_db.save_report(
            project_id=project_id or 1, report_id=job_id,
            category_name=category_name,
            company_count=len(cat_companies),
            model=model,
            markdown_content=result_data.get("report", ""),
        )
    elif result_data.get("status") == "error":
        report_db.save_report(
            project_id=project_id or 1, report_id=job_id,
            category_name=category_name,
            company_count=len(cat_companies),
            model=model, markdown_content=None,
            status="error",
            error_message=result_data.get("error", ""),
        )
    sync_to_git_async(f"Report generated: {category_name}")


@ai_bp.route("/api/ai/market-report", methods=["POST"])
def ai_market_report():
    from config import RESEARCH_MODEL
    data = request.json
    category_name = data.get("category_name", "").strip()
    project_id = data.get("project_id")
    model = data.get("model", RESEARCH_MODEL)
    if not category_name:
        return jsonify({"error": "category_name is required"}), 400

    report_id = start_async_job("report", _run_market_report, category_name, project_id, model)
    return jsonify({"report_id": report_id})


@ai_bp.route("/api/ai/market-report/<report_id>")
def get_market_report(report_id):
    return jsonify(poll_result("report", report_id))


# --- Saved Reports ---

@ai_bp.route("/api/reports")
def list_reports():
    project_id = request.args.get("project_id", type=int)
    reports = current_app.db.get_reports(project_id=project_id)
    for r in reports:
        r.pop("markdown_content", None)
    return jsonify(reports)


@ai_bp.route("/api/reports/<report_id>")
def get_report(report_id):
    report = current_app.db.get_report(report_id)
    if not report:
        return jsonify({"error": "Not found"}), 404
    return jsonify(report)


@ai_bp.route("/api/reports/<report_id>", methods=["DELETE"])
def delete_report(report_id):
    current_app.db.delete_report(report_id)
    result_path = DATA_DIR / f"report_{report_id}.json"
    result_path.unlink(missing_ok=True)
    return jsonify({"status": "ok"})


@ai_bp.route("/api/reports/<report_id>/export/md")
def export_report_md(report_id):
    import io
    from flask import send_file
    report = current_app.db.get_report(report_id)
    if not report or not report.get("markdown_content"):
        return jsonify({"error": "Report not found"}), 404
    md = report["markdown_content"]
    buf = io.BytesIO(md.encode("utf-8"))
    buf.seek(0)
    filename = f"report_{report['category_name'].replace(' ', '_')}_{report_id}.md"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="text/markdown")

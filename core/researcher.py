"""Call Claude CLI for per-company deep research."""
import json
import subprocess

from config import (
    CLAUDE_BIN, CLAUDE_COMMON_FLAGS, PROMPTS_DIR,
    RESEARCH_TIMEOUT,
)


def research_company(url, model="claude-opus-4-6"):
    """Run deep research on a single company URL via Claude CLI.

    Returns a dict with all extracted company fields.
    Raises RuntimeError on failure.
    """
    prompt_template = (PROMPTS_DIR / "research.txt").read_text()
    prompt = prompt_template.format(url=url)
    schema = (PROMPTS_DIR / "schemas" / "company_research.json").read_text()

    cmd = [
        CLAUDE_BIN,
        "-p", prompt,
        *CLAUDE_COMMON_FLAGS,
        "--json-schema", schema,
        "--tools", "WebSearch,WebFetch",
        "--model", model,
        "--no-session-persistence",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=RESEARCH_TIMEOUT,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()[:500] if result.stderr else "unknown error"
        raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {stderr}")

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse Claude CLI output: {e}\nRaw: {result.stdout[:500]}")

    if response.get("is_error"):
        raise RuntimeError(f"Claude CLI error: {response.get('result', 'unknown')[:300]}")

    structured = response.get("structured_output")
    if not structured:
        # Fall back to trying to parse the result text as JSON
        raw = response.get("result", "")
        try:
            structured = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raise ValueError(
                f"No structured output for {url}. Raw result: {raw[:300]}"
            )

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

    cmd = [
        CLAUDE_BIN,
        "-p", prompt,
        *CLAUDE_COMMON_FLAGS,
        "--json-schema", schema,
        "--tools", "WebSearch,WebFetch",
        "--model", model,
        "--no-session-persistence",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=RESEARCH_TIMEOUT,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()[:500] if result.stderr else "unknown error"
        raise RuntimeError(f"Re-research failed (exit {result.returncode}): {stderr}")

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse re-research output: {e}")

    if response.get("is_error"):
        raise RuntimeError(f"Re-research error: {response.get('result', 'unknown')[:300]}")

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

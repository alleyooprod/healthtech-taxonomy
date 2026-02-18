"""Pre-validation triage: scrape, assess relevance, flag issues."""
import json
import subprocess
from dataclasses import dataclass, asdict
from typing import Optional

from config import CLAUDE_BIN, CLAUDE_COMMON_FLAGS
from core.scraper import scrape_page, check_relevance, ScrapedPage
from core.url_resolver import resolve_shortened_url, AGGREGATOR_DOMAINS


@dataclass
class TriageResult:
    original_url: str
    resolved_url: str
    status: str  # 'valid' | 'suspect' | 'error'
    reason: str
    title: str
    meta_description: str
    scraped_text_preview: str  # First 200 chars for UI display
    is_accessible: bool

    def to_dict(self):
        return asdict(self)


def triage_single_url(url: str, use_claude_for_ambiguous: bool = True,
                      project_keywords: list[str] = None,
                      project_purpose: str = None) -> TriageResult:
    """Full triage for one URL: resolve -> scrape -> assess relevance.

    Args:
        url: The URL to triage
        use_claude_for_ambiguous: Whether to use Claude for ambiguous cases
        project_keywords: Project-specific keywords for relevance checking.
                         If provided, used INSTEAD of default MARKET_KEYWORDS.
        project_purpose: Project purpose/description for Claude assessment context.
    """
    # Step 1: Resolve shortened URLs
    resolved_url, resolve_ok = resolve_shortened_url(url)

    # Check if resolved URL is still an aggregator page
    if any(domain in resolved_url for domain in AGGREGATOR_DOMAINS):
        return TriageResult(
            original_url=url,
            resolved_url=resolved_url,
            status="suspect",
            reason="Could not resolve link-in-bio to company website",
            title="",
            meta_description="",
            scraped_text_preview="",
            is_accessible=True,
        )

    # Step 2: Scrape with Playwright
    scraped = scrape_page(resolved_url)

    if not scraped.is_accessible:
        return TriageResult(
            original_url=url,
            resolved_url=resolved_url,
            status="error",
            reason=scraped.error or f"HTTP {scraped.status_code}",
            title="",
            meta_description="",
            scraped_text_preview="",
            is_accessible=False,
        )

    # Step 3: Keyword-based relevance check (project-specific or default)
    status, reason = check_relevance(scraped, keywords=project_keywords)

    # Step 4: For suspect links, optionally use fast Claude call
    if status == "suspect" and use_claude_for_ambiguous:
        claude_status, claude_reason = _claude_quick_assess(
            scraped, project_purpose=project_purpose
        )
        status = claude_status
        reason = claude_reason

    return TriageResult(
        original_url=url,
        resolved_url=scraped.final_url,
        status=status,
        reason=reason,
        title=scraped.title,
        meta_description=scraped.meta_description,
        scraped_text_preview=scraped.main_text[:200],
        is_accessible=True,
    )


def triage_urls(urls: list[str], use_claude_for_ambiguous: bool = True,
                project_keywords: list[str] = None,
                project_purpose: str = None) -> list[TriageResult]:
    """Triage a list of URLs sequentially. Returns list of TriageResult."""
    results = []
    for url in urls:
        result = triage_single_url(
            url, use_claude_for_ambiguous,
            project_keywords=project_keywords,
            project_purpose=project_purpose,
        )
        results.append(result)
    return results


def _claude_quick_assess(scraped: ScrapedPage,
                         project_purpose: str = None) -> tuple[str, str]:
    """Use Claude Haiku for a fast relevance assessment on ambiguous pages."""
    context = project_purpose or (
        "a HEALTHTECH taxonomy covering: healthtech, digital health, wellness, "
        "fitness, nutrition, mental health, medical technology, wearables, "
        "diagnostics, telehealth, employee benefits/EAP, and health insurance"
    )

    prompt = f"""You are assessing whether a website belongs in {context}.

Website title: {scraped.title}
Meta description: {scraped.meta_description}
Page content preview: {scraped.main_text[:500]}

Does this company/website fit into this taxonomy?

Reply with ONLY valid JSON:
{{"relevant": true/false, "reason": "one sentence explanation"}}"""

    cmd = [
        CLAUDE_BIN,
        "-p",
        prompt,
        *CLAUDE_COMMON_FLAGS,
        "--model",
        "haiku",
        "--no-session-persistence",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            response = json.loads(result.stdout)
            text = response.get("result", "")
            # Try to extract JSON from the response
            try:
                assessment = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                # Try to find JSON in the text
                import re

                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    assessment = json.loads(match.group())
                else:
                    return "suspect", "Claude assessment inconclusive"

            if assessment.get("relevant"):
                return "valid", f"Claude: {assessment.get('reason', 'relevant')}"
            else:
                return "suspect", f"Claude: {assessment.get('reason', 'not relevant')}"
    except Exception:
        pass

    return "suspect", "Could not determine relevance"

"""Web scraping via Playwright for healthtech triage and research."""
import asyncio
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class ScrapedPage:
    url: str
    final_url: str
    title: str
    meta_description: str
    main_text: str  # First ~2000 chars of visible text
    status_code: int
    is_accessible: bool
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)


# Broad market keywords covering Olly's full sphere:
# Health, Insurance, HR/Benefits, Wearables, digital + physical services
MARKET_KEYWORDS = [
    # Health & wellness
    "health", "medical", "wellness", "fitness", "nutrition", "mental",
    "therapy", "diagnostic", "clinic", "hospital", "care", "physio",
    "pharmacy", "doctor", "patient", "longevity", "biomarker",
    "telehealth", "wearable", "genomic", "pharmaceutical", "clinical",
    "healthtech", "medtech", "digital health", "telemedicine", "recovery",
    "sleep", "stress", "mindfulness", "supplement", "vitamin", "gut",
    "metabolic", "cardiovascular",
    # Insurance
    "insurance", "insurtech", "underwriting", "claims", "coverage",
    "policyholder", "actuarial", "reinsurance",
    # HR / Employee Benefits / EAP
    "employee benefits", "eap", "employee assistance", "human resources",
    "hr platform", "people platform", "payroll", "employee wellbeing",
    "employee wellness", "workplace", "benefits administration",
    "group benefits", "employer", "workforce",
    # Adjacent
    "wearable", "iot", "connected device", "health data", "biometric",
]

# Keep backward compatibility alias
HEALTH_KEYWORDS = MARKET_KEYWORDS


async def _scrape_page_async(url: str, timeout_ms: int = 15000) -> ScrapedPage:
    """Async implementation: launch browser, navigate, extract content."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            response = await page.goto(
                url, wait_until="domcontentloaded", timeout=timeout_ms
            )
            status_code = response.status if response else 0
            final_url = page.url

            # Wait briefly for JS to render
            await page.wait_for_timeout(2000)

            title = await page.title() or ""

            meta_desc_el = await page.query_selector('meta[name="description"]')
            meta_description = ""
            if meta_desc_el:
                meta_description = (
                    await meta_desc_el.get_attribute("content") or ""
                )

            # Extract visible text (first 2000 chars)
            main_text = await page.evaluate(
                "() => document.body ? document.body.innerText.substring(0, 2000) : ''"
            )

            return ScrapedPage(
                url=url,
                final_url=final_url,
                title=title,
                meta_description=meta_description,
                main_text=main_text,
                status_code=status_code,
                is_accessible=(status_code < 400),
            )

        except Exception as e:
            return ScrapedPage(
                url=url,
                final_url=url,
                title="",
                meta_description="",
                main_text="",
                status_code=0,
                is_accessible=False,
                error=str(e),
            )
        finally:
            await browser.close()


def scrape_page(url: str, timeout_ms: int = 15000) -> ScrapedPage:
    """Synchronous wrapper around the async Playwright scraper."""
    return asyncio.run(_scrape_page_async(url, timeout_ms))


def check_relevance(scraped: ScrapedPage, keywords: list[str] = None) -> tuple[str, str]:
    """Quick keyword-based relevance check.

    Args:
        scraped: The scraped page data
        keywords: Custom keywords to check against. If None, uses MARKET_KEYWORDS.

    Returns:
        (status, reason) where status is 'valid', 'suspect', or 'error'
    """
    if not scraped.is_accessible:
        return "error", scraped.error or f"HTTP {scraped.status_code}"

    kw_list = keywords if keywords else MARKET_KEYWORDS

    combined = f"{scraped.title} {scraped.meta_description}".lower()
    if any(kw.lower() in combined for kw in kw_list):
        return "valid", "Relevant content detected in title/meta"

    # Also check body text (wider net)
    body_lower = scraped.main_text.lower()
    matches = [kw for kw in kw_list if kw.lower() in body_lower]
    if len(matches) >= 2:
        return "valid", f"Keywords found in body: {', '.join(matches[:5])}"

    if len(matches) == 1:
        return "suspect", f"Only one keyword found: {matches[0]}"

    return "suspect", "No relevant keywords found in page content"


# Backwards compatibility alias
check_health_relevance = check_relevance

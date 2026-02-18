"""Web scraping via Playwright for healthtech triage and research."""
import asyncio
import threading
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


# --- Browser pool: reuse a single Chromium instance per thread (#7, #21) ---

_browser_lock = threading.Lock()
_browser_instances: dict[int, tuple] = {}  # thread_id -> (playwright, browser, created_at)
_BROWSER_MAX_AGE = 300  # Recycle browser instances after 5 minutes

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _get_or_create_loop():
    """Get the running event loop or create one for this thread."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


async def _get_browser():
    """Get or create a reusable browser for the current thread, with TTL."""
    import time
    tid = threading.get_ident()
    now = time.time()

    with _browser_lock:
        entry = _browser_instances.get(tid)
    if entry:
        pw, browser, created_at = entry
        if browser.is_connected() and (now - created_at) < _BROWSER_MAX_AGE:
            return pw, browser
        # Stale or expired browser — close and recreate
        with _browser_lock:
            _browser_instances.pop(tid, None)
        try:
            await browser.close()
            await pw.stop()
        except Exception:
            pass

    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    with _browser_lock:
        _browser_instances[tid] = (pw, browser, now)
    return pw, browser


async def _close_browser():
    """Close the browser for the current thread."""
    tid = threading.get_ident()
    with _browser_lock:
        entry = _browser_instances.pop(tid, None)
    if entry:
        pw, browser, _created = entry
        try:
            await browser.close()
        except Exception:
            pass
        try:
            await pw.stop()
        except Exception:
            pass


def close_browser_sync():
    """Synchronous helper to close ALL browser instances. Call on shutdown."""
    loop = _get_or_create_loop()
    # Close all instances, not just the current thread's
    with _browser_lock:
        entries = list(_browser_instances.items())
        _browser_instances.clear()
    for _tid, entry in entries:
        pw, browser, _created = entry
        try:
            loop.run_until_complete(browser.close())
        except Exception:
            pass
        try:
            loop.run_until_complete(pw.stop())
        except Exception:
            pass


async def _scrape_page_async(url: str, timeout_ms: int = 15000) -> ScrapedPage:
    """Async implementation: reuse browser, create a new context per scrape.

    Timeout hierarchy (prevents any single URL from hanging indefinitely):
    - Per-operation: timeout_ms via context.set_default_timeout() — every
      Playwright call (goto, evaluate, querySelector, etc.) inherits this.
    - Overall deadline: 2× timeout_ms via asyncio.wait_for() in the sync
      wrapper — catches accumulated delays even when individual ops succeed.
    """
    try:
        _pw, browser = await _get_browser()
    except Exception as e:
        return ScrapedPage(
            url=url, final_url=url, title="", meta_description="",
            main_text="", status_code=0, is_accessible=False,
            error=f"Browser launch failed: {e}",
        )

    context = await browser.new_context(user_agent=_USER_AGENT)
    context.set_default_timeout(timeout_ms)
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
        await context.close()


def scrape_page(url: str, timeout_ms: int = 15000) -> ScrapedPage:
    """Synchronous wrapper with overall deadline.

    The deadline (2× timeout_ms) catches accumulated delays: even if goto
    takes 14s and evaluate takes 14s (both under 15s individually), the
    overall 30s deadline fires and returns an error instead of blocking.
    """
    loop = _get_or_create_loop()
    deadline_s = (timeout_ms * 2) / 1000
    try:
        return loop.run_until_complete(
            asyncio.wait_for(_scrape_page_async(url, timeout_ms), timeout=deadline_s)
        )
    except asyncio.TimeoutError:
        return ScrapedPage(
            url=url, final_url=url, title="", meta_description="",
            main_text="", status_code=0, is_accessible=False,
            error=f"Scrape deadline exceeded ({deadline_s:.0f}s)",
        )


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

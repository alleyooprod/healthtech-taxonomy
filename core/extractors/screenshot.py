"""Screenshot classifier — classify captured screenshots by journey stage and UI patterns.

Classifies screenshots into categories:
- Journey stages: onboarding, login, dashboard, settings, checkout, pricing, etc.
- UI patterns: form, table, chart, map, modal, navigation, empty-state, error

Uses metadata-based heuristics when no vision model is available,
or LLM analysis when the evidence source URL provides context.
"""
import json
import logging
import re
import time
from dataclasses import dataclass, asdict, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ── Journey Stage Definitions ────────────────────────────────

JOURNEY_STAGES = [
    "landing",       # Marketing/landing page
    "onboarding",    # Sign-up, welcome, setup wizard
    "login",         # Authentication screens
    "dashboard",     # Main dashboard/home
    "listing",       # Lists, tables, browse views
    "detail",        # Single item detail view
    "settings",      # Settings, preferences, account
    "checkout",      # Payment, checkout, billing
    "pricing",       # Pricing page
    "help",          # Help, docs, support
    "search",        # Search interface/results
    "profile",       # User profile
    "notification",  # Notifications, alerts
    "error",         # Error pages (404, 500, etc.)
    "empty",         # Empty states
    "other",         # Unclassified
]

UI_PATTERNS = [
    "form",          # Input forms
    "table",         # Data tables
    "chart",         # Charts, graphs, visualizations
    "map",           # Maps
    "modal",         # Overlays, modals, dialogs
    "navigation",    # Nav bars, sidebars, menus
    "card-grid",     # Card-based layouts
    "list",          # Simple lists
    "hero",          # Hero sections
    "empty-state",   # Empty/zero-data states
    "wizard",        # Multi-step wizards
    "timeline",      # Timeline views
]

# URL path patterns → journey stage mappings
_URL_STAGE_PATTERNS = {
    r"(?:^/?$|/home|/index)": "landing",
    r"/(?:signup|sign-up|register|onboard|welcome|get-started)": "onboarding",
    r"/(?:login|signin|sign-in|auth)": "login",
    r"/(?:dashboard|overview|home(?!page))": "dashboard",
    r"/(?:settings|preferences|account|profile/edit)": "settings",
    r"/(?:checkout|payment|billing|subscribe)": "checkout",
    r"/(?:pricing|plans|upgrade)": "pricing",
    r"/(?:help|docs|documentation|support|faq|knowledge)": "help",
    r"/(?:search|find|discover|explore)": "search",
    r"/(?:profile|user|me)": "profile",
    r"/(?:notifications?|alerts?)": "notification",
    r"/(?:404|500|error|not-found)": "error",
}


@dataclass
class ScreenshotClassification:
    """Classification result for a screenshot."""
    journey_stage: str = "other"
    journey_confidence: float = 0.0
    ui_patterns: list = field(default_factory=list)
    description: str = ""
    sequence_position: Optional[int] = None  # Position in a journey sequence
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def classify_by_url(source_url):
    """Classify a screenshot based on its source URL.

    Returns:
        ScreenshotClassification with URL-inferred stage
    """
    if not source_url:
        return ScreenshotClassification()

    parsed = urlparse(source_url)
    path = parsed.path.lower().rstrip("/")

    for pattern, stage in _URL_STAGE_PATTERNS.items():
        if re.search(pattern, path):
            return ScreenshotClassification(
                journey_stage=stage,
                journey_confidence=0.6,
                description=f"Classified from URL path: {path}",
                metadata={"method": "url_pattern", "url": source_url},
            )

    return ScreenshotClassification(
        journey_confidence=0.1,
        description=f"No URL pattern match for: {path}",
        metadata={"method": "url_pattern", "url": source_url},
    )


def classify_by_filename(filename):
    """Classify based on the evidence filename.

    Returns:
        ScreenshotClassification
    """
    if not filename:
        return ScreenshotClassification()

    name_lower = filename.lower()

    # Check for stage keywords in filename
    for stage in JOURNEY_STAGES:
        if stage in name_lower:
            return ScreenshotClassification(
                journey_stage=stage,
                journey_confidence=0.5,
                description=f"Matched stage keyword in filename: {filename}",
                metadata={"method": "filename_match"},
            )

    return ScreenshotClassification(
        journey_confidence=0.1,
        metadata={"method": "filename_match"},
    )


def classify_by_context(source_url=None, filename=None, source_name=None,
                        evidence_metadata=None):
    """Classify using all available context (URL, filename, metadata).

    Combines signals from URL patterns, filename hints, and metadata.
    Returns the highest-confidence classification.

    Args:
        source_url: Original URL where screenshot was captured
        filename: Evidence filename
        source_name: Source name (e.g. "App Store", "Website capture")
        evidence_metadata: dict of additional metadata

    Returns:
        ScreenshotClassification
    """
    candidates = []

    if source_url:
        candidates.append(classify_by_url(source_url))

    if filename:
        candidates.append(classify_by_filename(filename))

    # Check metadata for hints
    if evidence_metadata:
        title = evidence_metadata.get("title", "").lower()
        if title:
            for stage in JOURNEY_STAGES:
                if stage in title:
                    candidates.append(ScreenshotClassification(
                        journey_stage=stage,
                        journey_confidence=0.55,
                        description=f"Matched stage in page title: {title}",
                        metadata={"method": "title_match"},
                    ))
                    break

    if not candidates:
        return ScreenshotClassification()

    # Return the highest confidence classification
    best = max(candidates, key=lambda c: c.journey_confidence)
    return best


def classify_with_llm(content_description, source_url=None, model=None, timeout=60):
    """Classify a screenshot using LLM analysis of its context.

    This doesn't send the actual image — it uses the page title, URL,
    and any text metadata to classify. For actual image analysis,
    a vision model would be needed.

    Args:
        content_description: Text describing what's in the screenshot
            (page title, surrounding text, alt text)
        source_url: URL where screenshot was captured
        model: LLM model override
        timeout: LLM timeout

    Returns:
        ScreenshotClassification
    """
    from core.llm import run_cli
    from config import DEFAULT_MODEL

    # Use Haiku for classification — fast and cheap for this simple task
    model = model or DEFAULT_MODEL

    schema = {
        "type": "object",
        "properties": {
            "journey_stage": {
                "type": "string",
                "enum": JOURNEY_STAGES,
                "description": "The UI journey stage this screenshot represents",
            },
            "journey_confidence": {
                "type": "number", "minimum": 0, "maximum": 1,
            },
            "ui_patterns": {
                "type": "array",
                "items": {"type": "string", "enum": UI_PATTERNS},
                "description": "UI patterns visible in this screenshot",
            },
            "description": {
                "type": "string",
                "description": "Brief description of what this screen shows",
            },
        },
        "required": ["journey_stage", "journey_confidence"],
    }

    url_context = f"\nURL: {source_url}" if source_url else ""
    prompt = f"""Classify this UI screenshot based on the available context.

Context:{url_context}
Description: {content_description}

Determine:
1. What journey stage this represents (e.g. dashboard, settings, onboarding)
2. Your confidence in this classification (0-1)
3. What UI patterns are visible (form, table, chart, etc.)
4. A brief description of what this screen shows"""

    start = time.time()
    try:
        response = run_cli(
            prompt=prompt, model=model, timeout=timeout,
            json_schema=json.dumps(schema),
            operation="screenshot_classify",
        )
    except Exception as e:
        logger.error("Screenshot LLM classification failed: %s", e)
        return ScreenshotClassification()

    elapsed = int((time.time() - start) * 1000)

    if response.get("is_error"):
        return ScreenshotClassification()

    result = response.get("structured_output")
    if not result:
        return ScreenshotClassification()

    stage = result.get("journey_stage", "other")
    if stage not in JOURNEY_STAGES:
        stage = "other"

    patterns = [p for p in result.get("ui_patterns", []) if p in UI_PATTERNS]

    return ScreenshotClassification(
        journey_stage=stage,
        journey_confidence=max(0.0, min(1.0, result.get("journey_confidence", 0.5))),
        ui_patterns=patterns,
        description=result.get("description", ""),
        metadata={"method": "llm", "model": model, "duration_ms": elapsed},
    )


def group_into_sequences(classifications):
    """Group classified screenshots into likely journey sequences.

    Takes a list of (evidence_id, ScreenshotClassification) tuples
    and groups them into logical sequences.

    Args:
        classifications: list of (evidence_id, ScreenshotClassification)

    Returns:
        list of sequences: [{name, screenshots: [(evidence_id, classification), ...]}]
    """
    # Typical journey order
    STAGE_ORDER = {
        "landing": 0, "pricing": 1, "onboarding": 2, "login": 3,
        "dashboard": 4, "listing": 5, "detail": 6, "search": 7,
        "settings": 8, "profile": 9, "checkout": 10,
        "help": 11, "notification": 12, "error": 13, "empty": 14,
        "other": 15,
    }

    if not classifications:
        return []

    # Sort by stage order
    sorted_items = sorted(
        classifications,
        key=lambda x: STAGE_ORDER.get(x[1].journey_stage, 99),
    )

    # Group into sequences by breaking at "other" or large gaps
    sequences = []
    current_sequence = []

    for item in sorted_items:
        ev_id, classification = item
        if classification.journey_stage == "other" and current_sequence:
            sequences.append({
                "name": f"Journey: {current_sequence[0][1].journey_stage} → {current_sequence[-1][1].journey_stage}",
                "screenshots": current_sequence,
            })
            current_sequence = []
        current_sequence.append(item)

    if current_sequence:
        if len(current_sequence) == 1:
            name = current_sequence[0][1].journey_stage
        else:
            name = f"Journey: {current_sequence[0][1].journey_stage} → {current_sequence[-1][1].journey_stage}"
        sequences.append({
            "name": name,
            "screenshots": current_sequence,
        })

    return sequences

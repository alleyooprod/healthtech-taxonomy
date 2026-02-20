"""Tests for Screenshot Classification — URL-based, filename, context, sequences.

Covers:
- URL pattern classification
- Filename pattern classification
- Combined context classification
- LLM-based classification (mocked)
- Journey sequence grouping
- API endpoints: classify-screenshot, screenshot-sequences

Run: pytest tests/test_screenshot_classifier.py -v
Markers: db, extraction
"""
import json
import pytest
from unittest.mock import patch

from core.extractors.screenshot import (
    ScreenshotClassification,
    classify_by_url,
    classify_by_filename,
    classify_by_context,
    classify_with_llm,
    group_into_sequences,
    JOURNEY_STAGES,
    UI_PATTERNS,
)

pytestmark = [pytest.mark.db, pytest.mark.extraction]


# ═══════════════════════════════════════════════════════════════
# ScreenshotClassification Dataclass
# ═══════════════════════════════════════════════════════════════

class TestScreenshotClassification:
    """SCR-CLASS: ScreenshotClassification dataclass tests."""

    def test_default_values(self):
        sc = ScreenshotClassification()
        assert sc.journey_stage == "other"
        assert sc.journey_confidence == 0.0
        assert sc.ui_patterns == []
        assert sc.description == ""

    def test_to_dict(self):
        sc = ScreenshotClassification(
            journey_stage="dashboard",
            journey_confidence=0.8,
            ui_patterns=["chart", "table"],
        )
        d = sc.to_dict()
        assert isinstance(d, dict)
        assert d["journey_stage"] == "dashboard"
        assert d["ui_patterns"] == ["chart", "table"]


# ═══════════════════════════════════════════════════════════════
# URL Classification
# ═══════════════════════════════════════════════════════════════

class TestURLClassification:
    """SCR-URL: URL-based screenshot classification."""

    def test_dashboard_url(self):
        result = classify_by_url("https://app.example.com/dashboard")
        assert result.journey_stage == "dashboard"
        assert result.journey_confidence > 0.5

    def test_settings_url(self):
        result = classify_by_url("https://app.example.com/settings")
        assert result.journey_stage == "settings"

    def test_pricing_url(self):
        result = classify_by_url("https://example.com/pricing")
        assert result.journey_stage == "pricing"

    def test_login_url(self):
        result = classify_by_url("https://app.example.com/login")
        assert result.journey_stage == "login"

    def test_signup_url(self):
        result = classify_by_url("https://app.example.com/signup")
        assert result.journey_stage == "onboarding"

    def test_checkout_url(self):
        result = classify_by_url("https://app.example.com/checkout")
        assert result.journey_stage == "checkout"

    def test_help_url(self):
        result = classify_by_url("https://docs.example.com/help")
        assert result.journey_stage == "help"

    def test_search_url(self):
        result = classify_by_url("https://app.example.com/search?q=test")
        assert result.journey_stage == "search"

    def test_unknown_url(self):
        result = classify_by_url("https://example.com/random-page-xyz")
        assert result.journey_stage == "other"
        assert result.journey_confidence < 0.5

    def test_empty_url(self):
        result = classify_by_url("")
        assert result.journey_stage == "other"
        assert result.journey_confidence == 0.0

    def test_none_url(self):
        result = classify_by_url(None)
        assert result.journey_stage == "other"

    def test_landing_page(self):
        result = classify_by_url("https://example.com/")
        assert result.journey_stage == "landing"


# ═══════════════════════════════════════════════════════════════
# Filename Classification
# ═══════════════════════════════════════════════════════════════

class TestFilenameClassification:
    """SCR-FILE: Filename-based screenshot classification."""

    def test_dashboard_filename(self):
        result = classify_by_filename("app_dashboard_20260220.png")
        assert result.journey_stage == "dashboard"

    def test_settings_filename(self):
        result = classify_by_filename("settings_page_screenshot.png")
        assert result.journey_stage == "settings"

    def test_pricing_filename(self):
        result = classify_by_filename("pricing_comparison.png")
        assert result.journey_stage == "pricing"

    def test_unknown_filename(self):
        result = classify_by_filename("screenshot_abc123.png")
        assert result.journey_confidence < 0.3

    def test_empty_filename(self):
        result = classify_by_filename("")
        assert result.journey_stage == "other"

    def test_none_filename(self):
        result = classify_by_filename(None)
        assert result.journey_stage == "other"


# ═══════════════════════════════════════════════════════════════
# Combined Context Classification
# ═══════════════════════════════════════════════════════════════

class TestContextClassification:
    """SCR-CTX: Combined context classification."""

    def test_url_wins_over_filename(self):
        result = classify_by_context(
            source_url="https://app.example.com/dashboard",
            filename="random_screenshot.png",
        )
        assert result.journey_stage == "dashboard"

    def test_metadata_title_match(self):
        result = classify_by_context(
            evidence_metadata={"title": "App Settings - Preferences"},
        )
        assert result.journey_stage == "settings"

    def test_no_context(self):
        result = classify_by_context()
        assert result.journey_stage == "other"
        assert result.journey_confidence == 0.0

    def test_filename_only(self):
        result = classify_by_context(filename="checkout_step2.png")
        assert result.journey_stage == "checkout"

    def test_highest_confidence_wins(self):
        # URL gives 0.6 confidence, filename gives 0.5
        result = classify_by_context(
            source_url="https://app.example.com/pricing",
            filename="screenshot_landing.png",
        )
        # URL should win with higher confidence
        assert result.journey_stage == "pricing"


# ═══════════════════════════════════════════════════════════════
# LLM Classification (Mocked)
# ═══════════════════════════════════════════════════════════════

class TestLLMClassification:
    """SCR-LLM: LLM-based screenshot classification."""

    @patch("core.llm.run_cli")
    def test_successful_classification(self, mock_llm):
        mock_llm.return_value = {
            "result": "",
            "cost_usd": 0.002,
            "duration_ms": 500,
            "is_error": False,
            "structured_output": {
                "journey_stage": "dashboard",
                "journey_confidence": 0.85,
                "ui_patterns": ["chart", "table", "navigation"],
                "description": "Main analytics dashboard with revenue chart",
            },
        }

        result = classify_with_llm("Analytics Dashboard - Revenue Overview")
        assert result.journey_stage == "dashboard"
        assert result.journey_confidence == 0.85
        assert "chart" in result.ui_patterns
        assert result.metadata["method"] == "llm"

    @patch("core.llm.run_cli")
    def test_llm_error(self, mock_llm):
        mock_llm.return_value = {
            "result": "Error", "is_error": True,
            "cost_usd": 0, "duration_ms": 100,
            "structured_output": None,
        }
        result = classify_with_llm("Some description")
        assert result.journey_stage == "other"
        assert result.journey_confidence == 0.0

    @patch("core.llm.run_cli")
    def test_invalid_stage_normalised(self, mock_llm):
        mock_llm.return_value = {
            "result": "",
            "cost_usd": 0.001,
            "duration_ms": 300,
            "is_error": False,
            "structured_output": {
                "journey_stage": "invalid_stage",
                "journey_confidence": 0.5,
            },
        }
        result = classify_with_llm("Content")
        assert result.journey_stage == "other"

    @patch("core.llm.run_cli")
    def test_invalid_patterns_filtered(self, mock_llm):
        mock_llm.return_value = {
            "result": "",
            "cost_usd": 0.001,
            "duration_ms": 300,
            "is_error": False,
            "structured_output": {
                "journey_stage": "dashboard",
                "journey_confidence": 0.7,
                "ui_patterns": ["chart", "invalid_pattern", "table"],
            },
        }
        result = classify_with_llm("Dashboard")
        assert result.ui_patterns == ["chart", "table"]


# ═══════════════════════════════════════════════════════════════
# Journey Sequence Grouping
# ═══════════════════════════════════════════════════════════════

class TestSequenceGrouping:
    """SCR-SEQ: Screenshot sequence grouping."""

    def test_basic_sequence(self):
        classifications = [
            (1, ScreenshotClassification(journey_stage="landing", journey_confidence=0.8)),
            (2, ScreenshotClassification(journey_stage="onboarding", journey_confidence=0.7)),
            (3, ScreenshotClassification(journey_stage="dashboard", journey_confidence=0.9)),
        ]
        sequences = group_into_sequences(classifications)
        assert len(sequences) == 1
        assert len(sequences[0]["screenshots"]) == 3

    def test_empty_input(self):
        sequences = group_into_sequences([])
        assert sequences == []

    def test_single_screenshot(self):
        classifications = [
            (1, ScreenshotClassification(journey_stage="dashboard")),
        ]
        sequences = group_into_sequences(classifications)
        assert len(sequences) == 1
        assert sequences[0]["name"] == "dashboard"

    def test_sorts_by_stage_order(self):
        # Add screenshots out of order
        classifications = [
            (1, ScreenshotClassification(journey_stage="dashboard")),
            (2, ScreenshotClassification(journey_stage="landing")),
            (3, ScreenshotClassification(journey_stage="settings")),
        ]
        sequences = group_into_sequences(classifications)
        assert len(sequences) == 1
        # Should be sorted: landing → dashboard → settings
        stages = [sc[1].journey_stage for sc in sequences[0]["screenshots"]]
        assert stages[0] == "landing"
        assert stages[1] == "dashboard"
        assert stages[2] == "settings"

    def test_other_breaks_sequence(self):
        classifications = [
            (1, ScreenshotClassification(journey_stage="landing")),
            (2, ScreenshotClassification(journey_stage="dashboard")),
            (3, ScreenshotClassification(journey_stage="other")),
            (4, ScreenshotClassification(journey_stage="settings")),
        ]
        sequences = group_into_sequences(classifications)
        # "other" should break into separate sequences
        assert len(sequences) >= 2


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

class TestConstants:
    """SCR-CONST: Journey stages and UI patterns constants."""

    def test_journey_stages_complete(self):
        assert "landing" in JOURNEY_STAGES
        assert "dashboard" in JOURNEY_STAGES
        assert "settings" in JOURNEY_STAGES
        assert "checkout" in JOURNEY_STAGES
        assert "other" in JOURNEY_STAGES
        assert len(JOURNEY_STAGES) >= 10

    def test_ui_patterns_complete(self):
        assert "form" in UI_PATTERNS
        assert "table" in UI_PATTERNS
        assert "chart" in UI_PATTERNS
        assert len(UI_PATTERNS) >= 8


# ═══════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════

class TestScreenshotAPI:
    """SCR-API: Screenshot classification API tests."""

    @pytest.fixture
    def screenshot_project(self, client):
        """Project with entity and screenshot evidence."""
        schema = {
            "version": 1,
            "entity_types": [
                {"name": "Company", "slug": "company", "attributes": []},
            ],
            "relationships": [],
        }
        pid = client.db.create_project(
            name="Screenshot Test", entity_schema=schema,
        )
        eid = client.db.create_entity(pid, "company", "ScreenCo")

        # Add screenshot evidence records (no actual files needed for classification)
        ev1 = client.db.add_evidence(
            entity_id=eid,
            evidence_type="screenshot",
            file_path=f"{pid}/{eid}/screenshot/dashboard.png",
            source_url="https://app.screenco.com/dashboard",
            metadata=json.dumps({"title": "Dashboard - ScreenCo"}),
        )
        ev2 = client.db.add_evidence(
            entity_id=eid,
            evidence_type="screenshot",
            file_path=f"{pid}/{eid}/screenshot/settings.png",
            source_url="https://app.screenco.com/settings",
        )
        ev3 = client.db.add_evidence(
            entity_id=eid,
            evidence_type="screenshot",
            file_path=f"{pid}/{eid}/screenshot/pricing.png",
            source_url="https://screenco.com/pricing",
        )
        return {
            "client": client,
            "project_id": pid,
            "entity_id": eid,
            "evidence_ids": [ev1, ev2, ev3],
        }

    @pytest.mark.api
    def test_classify_single_screenshot(self, screenshot_project):
        c = screenshot_project["client"]
        eid = screenshot_project["entity_id"]
        ev_id = screenshot_project["evidence_ids"][0]

        r = c.post("/api/extract/classify-screenshot", json={
            "entity_id": eid,
            "evidence_id": ev_id,
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["journey_stage"] == "dashboard"
        assert data["evidence_id"] == ev_id

    @pytest.mark.api
    def test_classify_all_screenshots(self, screenshot_project):
        c = screenshot_project["client"]
        eid = screenshot_project["entity_id"]

        r = c.post("/api/extract/classify-screenshot", json={
            "entity_id": eid,
        })
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 3
        stages = {d["journey_stage"] for d in data}
        assert "dashboard" in stages
        assert "settings" in stages
        assert "pricing" in stages

    @pytest.mark.api
    def test_classify_missing_entity(self, screenshot_project):
        c = screenshot_project["client"]
        r = c.post("/api/extract/classify-screenshot", json={})
        assert r.status_code == 400

    @pytest.mark.api
    def test_classify_nonexistent_entity(self, screenshot_project):
        c = screenshot_project["client"]
        r = c.post("/api/extract/classify-screenshot", json={"entity_id": 99999})
        assert r.status_code == 404

    @pytest.mark.api
    def test_screenshot_sequences(self, screenshot_project):
        c = screenshot_project["client"]
        eid = screenshot_project["entity_id"]

        r = c.get(f"/api/extract/screenshot-sequences?entity_id={eid}")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
        # Should have at least one sequence
        assert len(data) >= 1
        # Each sequence should have screenshots
        for seq in data:
            assert "name" in seq
            assert "screenshots" in seq

    @pytest.mark.api
    def test_sequences_missing_entity(self, screenshot_project):
        c = screenshot_project["client"]
        r = c.get("/api/extract/screenshot-sequences")
        assert r.status_code == 400

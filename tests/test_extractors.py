"""Tests for document-specific extractors — classifiers, prompt building, extraction.

Covers:
- Product page extractor: prompt, schema, classify, extract (mocked LLM)
- Pricing page extractor: prompt, schema, classify, extract (mocked LLM)
- Generic extractor: prompt, schema, extract (mocked LLM)
- Classifier: classification routing, threshold, forced extractor
- API: /api/extract/classify, /api/extract/extractors

Run: pytest tests/test_extractors.py -v
Markers: db, extraction
"""
import json
import pytest
from unittest.mock import patch

from core.extractors import product_page, pricing_page, generic
from core.extractors.classifier import (
    classify_content,
    extract_with_classification,
    get_available_extractors,
    CLASSIFICATION_THRESHOLD,
)

pytestmark = [pytest.mark.db, pytest.mark.extraction]


# ═══════════════════════════════════════════════════════════════
# Product Page Extractor
# ═══════════════════════════════════════════════════════════════

class TestProductPageClassifier:
    """EXTR-PP-CLASS: Product page classification heuristics."""

    def test_marketing_page_high_confidence(self):
        content = """
        Get started with our platform today. Sign up for a free trial.
        Features include analytics, reporting, and integrations.
        How it works: connect your data, get insights.
        Trusted by 500+ customers including Fortune 500 companies.
        """
        score = product_page.classify(content)
        assert score >= 0.5

    def test_non_marketing_page_low_confidence(self):
        content = """
        This is a blog post about the history of software engineering.
        In 1968, the term was first used at a NATO conference.
        """
        score = product_page.classify(content)
        assert score < 0.3

    def test_empty_content(self):
        score = product_page.classify("")
        assert score == 0.0


class TestProductPagePrompt:
    """EXTR-PP-PROMPT: Product page prompt construction."""

    def test_prompt_includes_entity(self):
        prompt = product_page.build_prompt("content", "Acme Corp")
        assert "Acme Corp" in prompt
        assert "product or marketing" in prompt

    def test_prompt_without_entity(self):
        prompt = product_page.build_prompt("content")
        assert "product or marketing" in prompt


class TestProductPageExtraction:
    """EXTR-PP-EXTRACT: Product page extraction with mocked LLM."""

    @patch("core.llm.run_cli")
    def test_successful_extraction(self, mock_llm):
        mock_llm.return_value = {
            "result": "",
            "cost_usd": 0.004,
            "duration_ms": 1200,
            "is_error": False,
            "structured_output": {
                "company_name": "Acme Corp",
                "tagline": "The best SaaS platform",
                "description": "Enterprise SaaS for supply chain management",
                "target_audience": "Large enterprises",
                "key_features": ["Analytics", "Reporting", "Integrations"],
                "confidence": 0.95,
            },
        }

        result = product_page.extract("Some marketing page content", "Acme Corp")
        assert result is not None
        assert result["company_name"] == "Acme Corp"
        assert result["_meta"]["extractor"] == "product_page"

    @patch("core.llm.run_cli")
    def test_llm_error_returns_none(self, mock_llm):
        mock_llm.return_value = {
            "result": "Error", "is_error": True, "cost_usd": 0, "duration_ms": 100,
            "structured_output": None,
        }
        result = product_page.extract("Content")
        assert result is None

    @patch("core.llm.run_cli")
    def test_exception_returns_none(self, mock_llm):
        mock_llm.side_effect = RuntimeError("No CLI")
        result = product_page.extract("Content")
        assert result is None


# ═══════════════════════════════════════════════════════════════
# Pricing Page Extractor
# ═══════════════════════════════════════════════════════════════

class TestPricingPageClassifier:
    """EXTR-PR-CLASS: Pricing page classification heuristics."""

    def test_pricing_page_high_confidence(self):
        content = """
        Pricing Plans
        Basic: $9/month, Pro: $29/month, Enterprise: Contact sales
        All plans include a 14-day free trial.
        Billed annually: save 20%.
        Per user pricing, start with 5 users.
        """
        score = pricing_page.classify(content)
        assert score >= 0.7

    def test_non_pricing_low_confidence(self):
        content = "This is our company blog. Read about our latest updates."
        score = pricing_page.classify(content)
        assert score < 0.3

    def test_ambiguous_content(self):
        content = "Our enterprise solution has flexible pricing."
        score = pricing_page.classify(content)
        assert 0.0 <= score <= 1.0


class TestPricingPagePrompt:
    """EXTR-PR-PROMPT: Pricing page prompt construction."""

    def test_prompt_includes_entity(self):
        prompt = pricing_page.build_prompt("content", "Acme Corp")
        assert "Acme Corp" in prompt
        assert "pricing" in prompt.lower()

    def test_prompt_instructions(self):
        prompt = pricing_page.build_prompt("content")
        assert "billing" in prompt.lower() or "price" in prompt.lower()


class TestPricingPageExtraction:
    """EXTR-PR-EXTRACT: Pricing page extraction with mocked LLM."""

    @patch("core.llm.run_cli")
    def test_successful_extraction(self, mock_llm):
        mock_llm.return_value = {
            "result": "",
            "cost_usd": 0.003,
            "duration_ms": 1000,
            "is_error": False,
            "structured_output": {
                "has_pricing": True,
                "pricing_model": "subscription",
                "plans": [
                    {"name": "Basic", "price_monthly": "$9", "is_free": False},
                    {"name": "Pro", "price_monthly": "$29", "is_free": False},
                ],
                "has_free_tier": False,
                "has_free_trial": True,
                "trial_duration": "14 days",
                "confidence": 0.9,
            },
        }

        result = pricing_page.extract("Pricing page content")
        assert result is not None
        assert result["has_pricing"] is True
        assert len(result["plans"]) == 2
        assert result["_meta"]["extractor"] == "pricing_page"


# ═══════════════════════════════════════════════════════════════
# Generic Extractor
# ═══════════════════════════════════════════════════════════════

class TestGenericPrompt:
    """EXTR-GEN-PROMPT: Generic extractor prompt."""

    def test_prompt_structure(self):
        prompt = generic.build_prompt("Some content", "TestCo")
        assert "TestCo" in prompt
        assert "document" in prompt.lower()


class TestGenericExtraction:
    """EXTR-GEN-EXTRACT: Generic extraction with mocked LLM."""

    @patch("core.llm.run_cli")
    def test_successful_extraction(self, mock_llm):
        mock_llm.return_value = {
            "result": "",
            "cost_usd": 0.002,
            "duration_ms": 800,
            "is_error": False,
            "structured_output": {
                "document_type": "blog",
                "title": "Industry Update",
                "summary": "A blog post about market trends.",
                "key_facts": [
                    {"fact": "Market grew 15%", "category": "market"},
                ],
                "entities_mentioned": ["Acme Corp", "Beta Inc"],
            },
        }

        result = generic.extract("Blog post content")
        assert result is not None
        assert result["document_type"] == "blog"
        assert result["_meta"]["extractor"] == "generic"


# ═══════════════════════════════════════════════════════════════
# Classifier
# ═══════════════════════════════════════════════════════════════

class TestClassifier:
    """EXTR-CLASSIFY: Content classification and routing."""

    def test_pricing_content_routes_to_pricing(self):
        content = """
        Pricing: Basic $9/month, Pro $29/month, Enterprise custom.
        Free trial available. Billed annually save 20%.
        Per user pricing.
        """
        extractor, name, confidence = classify_content(content)
        assert name == "pricing_page"
        assert confidence >= CLASSIFICATION_THRESHOLD

    def test_product_content_routes_to_product(self):
        content = """
        Get started with our platform. Sign up for free.
        Features: Analytics, Reporting, Integrations.
        How it works: connect your data.
        Trusted by 1000+ customers. Request a demo today.
        """
        extractor, name, confidence = classify_content(content)
        assert name == "product_page"
        assert confidence >= CLASSIFICATION_THRESHOLD

    def test_generic_content_falls_through(self):
        content = "This is a random blog post about gardening techniques."
        extractor, name, confidence = classify_content(content)
        assert name == "generic"

    def test_empty_content(self):
        extractor, name, confidence = classify_content("")
        assert name == "generic"
        assert confidence == 0.0

    def test_available_extractors(self):
        extractors = get_available_extractors()
        assert "product_page" in extractors
        assert "pricing_page" in extractors
        assert "generic" in extractors

    @patch("core.llm.run_cli")
    def test_extract_with_classification(self, mock_llm):
        mock_llm.return_value = {
            "result": "",
            "cost_usd": 0.003,
            "duration_ms": 1000,
            "is_error": False,
            "structured_output": {
                "has_pricing": True,
                "pricing_model": "freemium",
                "plans": [],
                "confidence": 0.8,
            },
        }

        content = "Pricing: $9/month. Free trial. Billed annually. Per user."
        result = extract_with_classification(content, "TestCo")
        assert result is not None
        assert "_classification" in result

    @patch("core.llm.run_cli")
    def test_forced_extractor(self, mock_llm):
        mock_llm.return_value = {
            "result": "",
            "cost_usd": 0.002,
            "duration_ms": 700,
            "is_error": False,
            "structured_output": {
                "document_type": "other",
                "summary": "Test",
                "key_facts": [],
            },
        }

        result = extract_with_classification(
            "Any content", force_extractor="generic"
        )
        assert result is not None
        assert result["_classification"]["extractor"] == "generic"
        assert result["_classification"]["classification_confidence"] == 1.0


# ═══════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════

pytestmark_api = [pytest.mark.api, pytest.mark.extraction]


class TestExtractorsAPI:
    """EXTR-API: Extractor API endpoint tests."""

    @pytest.mark.api
    def test_list_extractors(self, client):
        r = client.get("/api/extract/extractors")
        assert r.status_code == 200
        data = r.get_json()
        assert "extractors" in data
        assert "product_page" in data["extractors"]
        assert "pricing_page" in data["extractors"]
        assert "generic" in data["extractors"]

    @pytest.mark.api
    @patch("core.llm.run_cli")
    def test_classify_endpoint(self, mock_llm, client):
        mock_llm.return_value = {
            "result": "",
            "cost_usd": 0.002,
            "duration_ms": 500,
            "is_error": False,
            "structured_output": {
                "document_type": "marketing",
                "summary": "A product page",
                "key_facts": [],
            },
        }

        r = client.post("/api/extract/classify", json={
            "content": "Some content to classify",
            "entity_name": "TestCo",
        })
        assert r.status_code == 200

    @pytest.mark.api
    def test_classify_missing_content(self, client):
        r = client.post("/api/extract/classify", json={})
        assert r.status_code == 400
        assert "content" in r.get_json()["error"]

    @pytest.mark.api
    @patch("core.llm.run_cli")
    def test_classify_with_forced_extractor(self, mock_llm, client):
        mock_llm.return_value = {
            "result": "",
            "cost_usd": 0.003,
            "duration_ms": 800,
            "is_error": False,
            "structured_output": {
                "has_pricing": True,
                "pricing_model": "subscription",
                "plans": [],
                "confidence": 0.8,
            },
        }

        r = client.post("/api/extract/classify", json={
            "content": "Some content",
            "force_extractor": "pricing_page",
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["_classification"]["extractor"] == "pricing_page"

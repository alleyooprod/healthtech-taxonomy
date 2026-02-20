"""Tests for schema refinement endpoint — AI-powered and rule-based.

Run: pytest tests/test_schema_refine.py -v
Markers: api, entities
"""
import json
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.api, pytest.mark.entities]

# ---------------------------------------------------------------------------
# Sample schemas used across tests
# ---------------------------------------------------------------------------

MINIMAL_SCHEMA = {
    "version": 1,
    "entity_types": [
        {
            "name": "Company",
            "slug": "company",
            "description": "A company",
            "icon": "building",
            "parent_type": None,
            "attributes": [
                {"name": "URL", "slug": "url", "data_type": "url", "required": True},
            ],
        },
    ],
    "relationships": [],
}

RICH_SCHEMA = {
    "version": 1,
    "entity_types": [
        {
            "name": "Company",
            "slug": "company",
            "description": "A company in the market",
            "icon": "building",
            "parent_type": None,
            "attributes": [
                {"name": "URL", "slug": "url", "data_type": "url", "required": True},
                {"name": "What they do", "slug": "what", "data_type": "text"},
                {"name": "Target market", "slug": "target", "data_type": "text"},
                {"name": "Funding stage", "slug": "funding_stage", "data_type": "text"},
                {"name": "Geography", "slug": "geography", "data_type": "text"},
                {"name": "Founded year", "slug": "founded_year", "data_type": "number"},
                {"name": "HQ country", "slug": "hq_country", "data_type": "text"},
                {"name": "Business model", "slug": "business_model", "data_type": "text"},
            ],
        },
        {
            "name": "Product",
            "slug": "product",
            "description": "A product",
            "icon": "package",
            "parent_type": "company",
            "attributes": [
                {"name": "Name", "slug": "name", "data_type": "text", "required": True},
                {"name": "Platform", "slug": "platform", "data_type": "text"},
                {"name": "Description", "slug": "description", "data_type": "text"},
                {"name": "URL", "slug": "url", "data_type": "url"},
                {"name": "Category", "slug": "category", "data_type": "text"},
                {"name": "Rating", "slug": "rating", "data_type": "number"},
                {"name": "Launch date", "slug": "launch_date", "data_type": "date"},
                {"name": "Pricing model", "slug": "pricing_model", "data_type": "text"},
            ],
        },
    ],
    "relationships": [
        {
            "name": "competes_with",
            "from_type": "company",
            "to_type": "company",
            "description": "Competitive relationship",
        },
    ],
}

SPARSE_SCHEMA = {
    "version": 1,
    "entity_types": [
        {
            "name": "Company",
            "slug": "company",
            "description": "A company",
            "icon": "building",
            "parent_type": None,
            "attributes": [
                {"name": "Name", "slug": "name", "data_type": "text", "required": True},
            ],
        },
        {
            "name": "Product",
            "slug": "product",
            "description": "A product",
            "icon": "package",
            "parent_type": "company",
            "attributes": [
                {"name": "Name", "slug": "name", "data_type": "text", "required": True},
            ],
        },
    ],
    "relationships": [],
}


# Mock LLM response for AI refine
MOCK_AI_REFINE_RESPONSE = {
    "result": "",
    "cost_usd": 0.01,
    "duration_ms": 2000,
    "is_error": False,
    "structured_output": {
        "suggestions": [
            {
                "type": "add_type",
                "target": None,
                "suggestion": "Add a 'Feature' entity type as child of 'Product'",
                "reasoning": "Features are the unit of comparison in competitive analysis",
                "schema_change": {
                    "slug": "feature",
                    "name": "Feature",
                    "parent_type": "product",
                    "attributes": [
                        {"name": "Name", "slug": "name", "data_type": "text", "required": True},
                        {"name": "Included", "slug": "included", "data_type": "boolean"},
                    ],
                },
            },
            {
                "type": "add_attribute",
                "target": "company",
                "suggestion": "Add 'regulatory_status' attribute to Company",
                "reasoning": "Regulatory status is critical for insurtech companies",
                "schema_change": {
                    "slug": "regulatory_status",
                    "name": "Regulatory Status",
                    "data_type": "enum",
                    "enum_values": ["authorized", "pending", "exempt"],
                },
            },
            {
                "type": "modify_attribute",
                "target": "product.pricing_model",
                "suggestion": "Change pricing_model from text to enum",
                "reasoning": "Standard pricing patterns enable better comparison",
                "schema_change": {
                    "data_type": "enum",
                    "enum_values": ["subscription", "per_policy", "commission", "freemium"],
                },
            },
        ],
        "challenges": [
            "No way to track product features separately",
            "Consider adding temporal attributes for trend analysis",
        ],
        "completeness_score": 0.6,
        "completeness_areas": {
            "entity_coverage": 0.5,
            "attribute_depth": 0.7,
            "relationship_richness": 0.4,
            "analysis_readiness": 0.6,
        },
    },
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def refine_project(client):
    """Create a project with a schema for refinement tests."""
    pid = client.db.create_project(
        name="Refine Test Project",
        purpose="Testing schema refinement",
        entity_schema=RICH_SCHEMA,
    )
    return {"id": pid, "client": client}


@pytest.fixture
def minimal_project(client):
    """Create a project with a minimal schema."""
    pid = client.db.create_project(
        name="Minimal Project",
        purpose="Testing sparse schema",
        entity_schema=MINIMAL_SCHEMA,
    )
    return {"id": pid, "client": client}


@pytest.fixture
def sparse_project(client):
    """Create a project with sparse attributes."""
    pid = client.db.create_project(
        name="Sparse Project",
        purpose="Testing sparse attributes",
        entity_schema=SPARSE_SCHEMA,
    )
    return {"id": pid, "client": client}


# ---------------------------------------------------------------------------
# AI-Powered Refinement (mocked LLM)
# ---------------------------------------------------------------------------

class TestSchemaRefineAI:
    """REFINE-AI: AI schema refinement with mocked LLM."""

    @patch("core.llm.run_cli")
    def test_refine_returns_suggestions(self, mock_run_cli, refine_project):
        """AI refine returns suggestions, challenges, and scores."""
        mock_run_cli.return_value = MOCK_AI_REFINE_RESPONSE
        c = refine_project["client"]
        pid = refine_project["id"]

        r = c.post("/api/schema/refine", json={
            "project_id": pid,
            "current_schema": RICH_SCHEMA,
            "research_goal": "Market analysis of insurtech startups",
        })
        assert r.status_code == 200
        data = r.get_json()

        assert "suggestions" in data
        assert "challenges" in data
        assert "completeness_score" in data
        assert "completeness_areas" in data

        assert len(data["suggestions"]) == 3
        assert len(data["challenges"]) == 2
        assert data["completeness_score"] == 0.6

        areas = data["completeness_areas"]
        assert areas["entity_coverage"] == 0.5
        assert areas["attribute_depth"] == 0.7
        assert areas["relationship_richness"] == 0.4
        assert areas["analysis_readiness"] == 0.6

    @patch("core.llm.run_cli")
    def test_refine_suggestion_types(self, mock_run_cli, refine_project):
        """AI suggestions include expected types."""
        mock_run_cli.return_value = MOCK_AI_REFINE_RESPONSE
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
            "research_goal": "Insurtech market analysis",
        })
        data = r.get_json()
        types = {s["type"] for s in data["suggestions"]}
        assert "add_type" in types
        assert "add_attribute" in types
        assert "modify_attribute" in types

    @patch("core.llm.run_cli")
    def test_refine_suggestion_has_schema_change(self, mock_run_cli, refine_project):
        """Each suggestion includes a schema_change dict."""
        mock_run_cli.return_value = MOCK_AI_REFINE_RESPONSE
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
            "research_goal": "Insurtech",
        })
        data = r.get_json()
        for s in data["suggestions"]:
            assert "schema_change" in s
            assert isinstance(s["schema_change"], dict)
            assert "reasoning" in s
            assert "suggestion" in s

    @patch("core.llm.run_cli")
    def test_refine_with_feedback(self, mock_run_cli, refine_project):
        """Refine accepts user feedback for iteration."""
        mock_run_cli.return_value = MOCK_AI_REFINE_RESPONSE
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
            "research_goal": "Insurtech analysis",
            "feedback": "I don't need a Feature entity, focus on regulatory attributes",
        })
        assert r.status_code == 200
        data = r.get_json()
        assert "suggestions" in data

        # Verify feedback was passed to LLM prompt
        call_args = mock_run_cli.call_args
        prompt = call_args.kwargs.get("prompt") or call_args[1].get("prompt") or call_args[0][0]
        assert "I don't need a Feature entity" in prompt

    @patch("core.llm.run_cli")
    def test_refine_clamps_scores(self, mock_run_cli, refine_project):
        """Scores are clamped to 0-1 range."""
        response = {
            **MOCK_AI_REFINE_RESPONSE,
            "structured_output": {
                **MOCK_AI_REFINE_RESPONSE["structured_output"],
                "completeness_score": 1.5,
                "completeness_areas": {
                    "entity_coverage": -0.2,
                    "attribute_depth": 1.3,
                    "relationship_richness": 0.5,
                    "analysis_readiness": 2.0,
                },
            },
        }
        mock_run_cli.return_value = response
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
            "research_goal": "Test",
        })
        data = r.get_json()
        assert data["completeness_score"] == 1.0
        assert data["completeness_areas"]["entity_coverage"] == 0.0
        assert data["completeness_areas"]["attribute_depth"] == 1.0
        assert data["completeness_areas"]["analysis_readiness"] == 1.0

    @patch("core.llm.run_cli")
    def test_refine_includes_cost(self, mock_run_cli, refine_project):
        """Response includes cost_usd from LLM."""
        mock_run_cli.return_value = MOCK_AI_REFINE_RESPONSE
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
            "research_goal": "Test",
        })
        data = r.get_json()
        assert "cost_usd" in data
        assert data["cost_usd"] == 0.01


# ---------------------------------------------------------------------------
# Fallback: Rule-Based Refinement
# ---------------------------------------------------------------------------

class TestSchemaRefineRuleBased:
    """REFINE-RULES: Rule-based fallback when LLM is unavailable."""

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_fallback_to_rule_based(self, mock_run_cli, refine_project):
        """When LLM fails, falls back to rule-based analysis."""
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
            "research_goal": "Market analysis",
        })
        assert r.status_code == 200
        data = r.get_json()

        assert "suggestions" in data
        assert "challenges" in data
        assert "completeness_score" in data
        assert "completeness_areas" in data

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_rule_based_detects_single_entity_type(self, mock_run_cli, minimal_project):
        """Rule-based detects schemas with < 2 entity types."""
        c = minimal_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": minimal_project["id"],
            "current_schema": MINIMAL_SCHEMA,
            "research_goal": "Test",
        })
        data = r.get_json()

        # Should challenge having only one entity type
        challenge_text = " ".join(data["challenges"])
        assert "only one entity type" in challenge_text.lower() or \
               "single entity type" in challenge_text.lower() or \
               "one entity type" in challenge_text.lower()

        # Should suggest adding a child type
        add_type_suggestions = [s for s in data["suggestions"] if s["type"] == "add_type"]
        assert len(add_type_suggestions) >= 1

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_rule_based_detects_sparse_attributes(self, mock_run_cli, sparse_project):
        """Rule-based detects entity types with < 3 attributes."""
        c = sparse_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": sparse_project["id"],
            "current_schema": SPARSE_SCHEMA,
            "research_goal": "Test",
        })
        data = r.get_json()

        # Should flag sparse attributes
        has_sparse_challenge = any(
            "sparse" in ch.lower() or "attribute" in ch.lower()
            for ch in data["challenges"]
        )
        assert has_sparse_challenge

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_rule_based_detects_missing_url(self, mock_run_cli, client):
        """Rule-based detects missing URL/website attribute."""
        no_url_schema = {
            "version": 1,
            "entity_types": [
                {
                    "name": "Company",
                    "slug": "company",
                    "parent_type": None,
                    "attributes": [
                        {"name": "Name", "slug": "name", "data_type": "text"},
                        {"name": "Description", "slug": "description", "data_type": "text"},
                        {"name": "Revenue", "slug": "revenue", "data_type": "currency"},
                    ],
                },
            ],
            "relationships": [],
        }
        pid = client.db.create_project(
            name="No URL Project",
            purpose="Test",
            entity_schema=no_url_schema,
        )

        r = client.post("/api/schema/refine", json={
            "project_id": pid,
            "current_schema": no_url_schema,
            "research_goal": "Test",
        })
        data = r.get_json()

        # Should suggest adding URL
        url_suggestions = [
            s for s in data["suggestions"]
            if "url" in s["suggestion"].lower() or "website" in s["suggestion"].lower()
        ]
        assert len(url_suggestions) >= 1

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_rule_based_detects_text_that_should_be_enum(self, mock_run_cli, client):
        """Rule-based identifies text attributes that should be enums."""
        enum_candidate_schema = {
            "version": 1,
            "entity_types": [
                {
                    "name": "Company",
                    "slug": "company",
                    "parent_type": None,
                    "attributes": [
                        {"name": "URL", "slug": "url", "data_type": "url"},
                        {"name": "Funding stage", "slug": "funding_stage", "data_type": "text"},
                        {"name": "Company status", "slug": "company_status", "data_type": "text"},
                        {"name": "Business model", "slug": "business_model", "data_type": "text"},
                    ],
                },
            ],
            "relationships": [],
        }
        pid = client.db.create_project(
            name="Enum Candidate",
            purpose="Test",
            entity_schema=enum_candidate_schema,
        )

        r = client.post("/api/schema/refine", json={
            "project_id": pid,
            "current_schema": enum_candidate_schema,
            "research_goal": "Test",
        })
        data = r.get_json()

        # Should suggest modifying text to enum
        modify_suggestions = [s for s in data["suggestions"] if s["type"] == "modify_attribute"]
        assert len(modify_suggestions) >= 1
        # The modify suggestion should mention enum
        assert any("enum" in s["suggestion"].lower() for s in modify_suggestions)

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_rule_based_detects_missing_relationships(self, mock_run_cli, sparse_project):
        """Rule-based identifies schemas with no relationships between types."""
        c = sparse_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": sparse_project["id"],
            "current_schema": SPARSE_SCHEMA,
            "research_goal": "Test",
        })
        data = r.get_json()

        # Should challenge lack of relationships
        has_rel_challenge = any(
            "relationship" in ch.lower() for ch in data["challenges"]
        )
        assert has_rel_challenge

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_rule_based_limits_suggestions_to_six(self, mock_run_cli, client):
        """Rule-based caps suggestions at 6."""
        # Schema designed to trigger many suggestions
        many_issues_schema = {
            "version": 1,
            "entity_types": [
                {
                    "name": "Thing A",
                    "slug": "thing-a",
                    "parent_type": None,
                    "attributes": [
                        {"name": "Status", "slug": "status", "data_type": "text"},
                    ],
                },
                {
                    "name": "Thing B",
                    "slug": "thing-b",
                    "parent_type": None,
                    "attributes": [
                        {"name": "Type", "slug": "type", "data_type": "text"},
                    ],
                },
                {
                    "name": "Thing C",
                    "slug": "thing-c",
                    "parent_type": None,
                    "attributes": [
                        {"name": "Level", "slug": "level", "data_type": "text"},
                    ],
                },
            ],
            "relationships": [],
        }
        pid = client.db.create_project(
            name="Many Issues",
            purpose="Test",
            entity_schema=many_issues_schema,
        )

        r = client.post("/api/schema/refine", json={
            "project_id": pid,
            "current_schema": many_issues_schema,
            "research_goal": "Test",
        })
        data = r.get_json()
        assert len(data["suggestions"]) <= 6


# ---------------------------------------------------------------------------
# Completeness Scoring
# ---------------------------------------------------------------------------

class TestCompletenessScoring:
    """REFINE-SCORE: Completeness scoring logic."""

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_minimal_schema_low_score(self, mock_run_cli, minimal_project):
        """A minimal schema gets a low completeness score."""
        c = minimal_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": minimal_project["id"],
            "current_schema": MINIMAL_SCHEMA,
            "research_goal": "Test",
        })
        data = r.get_json()
        assert data["completeness_score"] < 0.4

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_rich_schema_higher_score(self, mock_run_cli, refine_project):
        """A rich schema gets a higher completeness score."""
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
            "research_goal": "Test",
        })
        data = r.get_json()
        assert data["completeness_score"] > 0.3

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_completeness_areas_present(self, mock_run_cli, refine_project):
        """All four completeness areas are present and between 0-1."""
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
            "research_goal": "Test",
        })
        data = r.get_json()
        areas = data["completeness_areas"]
        for key in ["entity_coverage", "attribute_depth", "relationship_richness", "analysis_readiness"]:
            assert key in areas
            assert 0.0 <= areas[key] <= 1.0

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_relationships_increase_richness_score(self, mock_run_cli, client):
        """Schema with relationships scores higher on relationship_richness."""
        # Without relationships
        no_rels = {
            "version": 1,
            "entity_types": [
                {"name": "A", "slug": "a", "parent_type": None,
                 "attributes": [{"name": "x", "slug": "x", "data_type": "text"}]},
                {"name": "B", "slug": "b", "parent_type": None,
                 "attributes": [{"name": "y", "slug": "y", "data_type": "text"}]},
            ],
            "relationships": [],
        }
        pid1 = client.db.create_project(name="No Rels", purpose="T", entity_schema=no_rels)
        r1 = client.post("/api/schema/refine", json={
            "project_id": pid1, "current_schema": no_rels, "research_goal": "T",
        })
        score_no_rels = r1.get_json()["completeness_areas"]["relationship_richness"]

        # With relationships
        with_rels = {**no_rels, "relationships": [
            {"name": "relates", "from_type": "a", "to_type": "b"},
            {"name": "depends", "from_type": "b", "to_type": "a"},
        ]}
        pid2 = client.db.create_project(name="With Rels", purpose="T", entity_schema=with_rels)
        r2 = client.post("/api/schema/refine", json={
            "project_id": pid2, "current_schema": with_rels, "research_goal": "T",
        })
        score_with_rels = r2.get_json()["completeness_areas"]["relationship_richness"]

        assert score_with_rels > score_no_rels


# ---------------------------------------------------------------------------
# Validation & Error Handling
# ---------------------------------------------------------------------------

class TestSchemaRefineValidation:
    """REFINE-VALID: Input validation for refine endpoint."""

    def test_refine_requires_project_id(self, client):
        """project_id is required."""
        r = client.post("/api/schema/refine", json={
            "current_schema": MINIMAL_SCHEMA,
            "research_goal": "Test",
        })
        assert r.status_code == 400
        assert "project_id" in r.get_json()["error"]

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_refine_loads_schema_from_project(self, mock_run_cli, refine_project):
        """When current_schema is omitted, it loads from the project."""
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "research_goal": "Market analysis",
        })
        assert r.status_code == 200
        data = r.get_json()
        assert "suggestions" in data

    def test_refine_requires_schema(self, client):
        """When project has no schema and none provided, returns 400."""
        pid = client.db.create_project(name="Empty", purpose="T")

        r = client.post("/api/schema/refine", json={
            "project_id": pid,
            "research_goal": "Test",
        })
        assert r.status_code == 400
        assert "schema" in r.get_json()["error"].lower()

    @patch("core.llm.run_cli", side_effect=RuntimeError("LLM unavailable"))
    def test_refine_without_research_goal(self, mock_run_cli, refine_project):
        """Refine works without a research goal (optional)."""
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
        })
        assert r.status_code == 200
        data = r.get_json()
        assert "suggestions" in data

    @patch("core.llm.run_cli")
    def test_refine_llm_no_structured_output(self, mock_run_cli, refine_project):
        """When LLM returns no structured_output, falls back to rule-based."""
        mock_run_cli.return_value = {
            "result": "some text",
            "cost_usd": 0,
            "duration_ms": 100,
            "is_error": False,
            "structured_output": None,
        }
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
            "research_goal": "Test",
        })
        # Should fall back to rule-based (not error out)
        assert r.status_code == 200
        data = r.get_json()
        assert "suggestions" in data

    @patch("core.llm.run_cli")
    def test_refine_llm_is_error(self, mock_run_cli, refine_project):
        """When LLM returns is_error=True, falls back to rule-based."""
        mock_run_cli.return_value = {
            "result": "Rate limited",
            "cost_usd": 0,
            "duration_ms": 100,
            "is_error": True,
        }
        c = refine_project["client"]

        r = c.post("/api/schema/refine", json={
            "project_id": refine_project["id"],
            "current_schema": RICH_SCHEMA,
            "research_goal": "Test",
        })
        assert r.status_code == 200
        data = r.get_json()
        assert "suggestions" in data

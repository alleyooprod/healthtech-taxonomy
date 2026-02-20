"""Tests for Human Review Interface — DB layer enhancements.

Covers:
- get_review_queue_grouped: entity grouping, confidence filters, entity filter
- flag_needs_evidence: flag/unflag extraction results
- get_needs_evidence_results: query flagged results
- Enhanced extraction stats: confidence distribution, needs_evidence count

Run: pytest tests/test_review.py -v
Markers: db, extraction
"""
import json
import pytest

pytestmark = [pytest.mark.db, pytest.mark.extraction]


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

REVIEW_SCHEMA = {
    "version": 1,
    "entity_types": [
        {
            "name": "Company",
            "slug": "company",
            "description": "A company",
            "icon": "building",
            "parent_type": None,
            "attributes": [
                {"name": "Description", "slug": "description", "data_type": "text"},
                {"name": "Website", "slug": "website_url", "data_type": "url"},
                {"name": "Founded Year", "slug": "founded_year", "data_type": "number"},
                {"name": "Headquarters", "slug": "headquarters", "data_type": "text"},
            ],
        },
    ],
    "relationships": [],
}


@pytest.fixture
def review_db(tmp_path):
    """Database with project, entities, and extraction results for review testing."""
    from storage.db import Database
    db = Database(db_path=tmp_path / "test.db")

    pid = db.create_project(
        name="Review Test Project",
        purpose="Testing review queue",
        entity_schema=REVIEW_SCHEMA,
    )

    # Create two entities
    e1 = db.create_entity(pid, "company", "Acme Corp")
    e2 = db.create_entity(pid, "company", "Beta Inc")

    # Create extraction jobs
    j1 = db.create_extraction_job(pid, e1, source_type="evidence")
    db.update_extraction_job(j1, status="completed")
    j2 = db.create_extraction_job(pid, e2, source_type="url", source_ref="https://beta.com")
    db.update_extraction_job(j2, status="completed")

    # Create extraction results with varying confidence
    # Acme Corp: high + medium confidence
    r1 = db.create_extraction_result(j1, e1, "description", "Cloud platform", confidence=0.95, reasoning="Found on homepage")
    r2 = db.create_extraction_result(j1, e1, "headquarters", "London", confidence=0.7, reasoning="Inferred from contact page")
    r3 = db.create_extraction_result(j1, e1, "founded_year", "2018", confidence=0.85, reasoning="About page")

    # Beta Inc: medium + low confidence
    r4 = db.create_extraction_result(j2, e2, "description", "Fintech startup", confidence=0.6, reasoning="General page content")
    r5 = db.create_extraction_result(j2, e2, "website_url", "https://beta.com", confidence=0.4, reasoning="URL matched")
    r6 = db.create_extraction_result(j2, e2, "headquarters", "Berlin", confidence=0.3, reasoning="Very uncertain")

    return {
        "db": db,
        "project_id": pid,
        "entity_ids": [e1, e2],
        "job_ids": [j1, j2],
        "result_ids": [r1, r2, r3, r4, r5, r6],
    }


# ═══════════════════════════════════════════════════════════════
# Grouped Review Queue
# ═══════════════════════════════════════════════════════════════

class TestGroupedReviewQueue:
    """REV-DB-QUEUE: Grouped review queue tests."""

    def test_grouped_queue_returns_all_entities(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        groups = db.get_review_queue_grouped(pid)
        assert len(groups) == 2
        names = {g["entity_name"] for g in groups}
        assert names == {"Acme Corp", "Beta Inc"}

    def test_grouped_queue_includes_results(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        groups = db.get_review_queue_grouped(pid)
        total_results = sum(len(g["results"]) for g in groups)
        assert total_results == 6

    def test_grouped_queue_result_has_entity_context(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        groups = db.get_review_queue_grouped(pid)
        for g in groups:
            assert "entity_id" in g
            assert "entity_name" in g
            assert "entity_type" in g
            for r in g["results"]:
                assert "attr_slug" in r
                assert "extracted_value" in r
                assert "confidence" in r

    def test_grouped_queue_high_confidence_filter(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        groups = db.get_review_queue_grouped(pid, min_confidence=0.8)
        # Acme: description (0.95), founded_year (0.85)
        total = sum(len(g["results"]) for g in groups)
        assert total == 2
        assert len(groups) == 1
        assert groups[0]["entity_name"] == "Acme Corp"

    def test_grouped_queue_low_confidence_filter(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        groups = db.get_review_queue_grouped(pid, max_confidence=0.499)
        # Beta: website_url (0.4), headquarters (0.3)
        total = sum(len(g["results"]) for g in groups)
        assert total == 2
        assert len(groups) == 1
        assert groups[0]["entity_name"] == "Beta Inc"

    def test_grouped_queue_medium_confidence_filter(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        groups = db.get_review_queue_grouped(pid, min_confidence=0.5, max_confidence=0.799)
        # Acme: headquarters (0.7), Beta: description (0.6)
        total = sum(len(g["results"]) for g in groups)
        assert total == 2

    def test_grouped_queue_entity_filter(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        e1 = review_db["entity_ids"][0]
        groups = db.get_review_queue_grouped(pid, entity_id=e1)
        assert len(groups) == 1
        assert groups[0]["entity_name"] == "Acme Corp"
        assert len(groups[0]["results"]) == 3

    def test_grouped_queue_empty_after_all_reviewed(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        # Accept all results
        for rid in review_db["result_ids"]:
            db.review_extraction_result(rid, "accept")
        groups = db.get_review_queue_grouped(pid)
        assert len(groups) == 0

    def test_grouped_queue_respects_limit(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        # Limit to 3 results — may get partial entity groups
        groups = db.get_review_queue_grouped(pid, limit=3)
        total = sum(len(g["results"]) for g in groups)
        assert total <= 3

    def test_grouped_queue_includes_evidence_info(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        groups = db.get_review_queue_grouped(pid)
        # Results should have evidence-related fields (may be None if no evidence linked)
        for g in groups:
            for r in g["results"]:
                assert "source_type" in r
                # evidence_url, evidence_type_name may be None (no evidence linked)


# ═══════════════════════════════════════════════════════════════
# Needs Evidence Flag
# ═══════════════════════════════════════════════════════════════

class TestNeedsEvidenceFlag:
    """REV-DB-FLAG: Needs evidence flag tests."""

    def test_flag_needs_evidence(self, review_db):
        db = review_db["db"]
        r1 = review_db["result_ids"][0]
        assert db.flag_needs_evidence(r1, needs=True)
        result = db.get_extraction_result(r1)
        assert result["needs_evidence"] == 1

    def test_unflag_needs_evidence(self, review_db):
        db = review_db["db"]
        r1 = review_db["result_ids"][0]
        db.flag_needs_evidence(r1, needs=True)
        db.flag_needs_evidence(r1, needs=False)
        result = db.get_extraction_result(r1)
        assert result["needs_evidence"] == 0

    def test_flag_nonexistent_result(self, review_db):
        db = review_db["db"]
        assert not db.flag_needs_evidence(99999, needs=True)

    def test_get_needs_evidence_results(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        r1 = review_db["result_ids"][0]
        r4 = review_db["result_ids"][3]

        db.flag_needs_evidence(r1, needs=True)
        db.flag_needs_evidence(r4, needs=True)

        flagged = db.get_needs_evidence_results(pid)
        assert len(flagged) == 2
        flagged_ids = {r["id"] for r in flagged}
        assert r1 in flagged_ids
        assert r4 in flagged_ids

    def test_get_needs_evidence_includes_entity_context(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        r1 = review_db["result_ids"][0]
        db.flag_needs_evidence(r1, needs=True)

        flagged = db.get_needs_evidence_results(pid)
        assert len(flagged) == 1
        assert flagged[0]["entity_name"] == "Acme Corp"
        assert flagged[0]["entity_type"] == "company"

    def test_get_needs_evidence_empty_when_none_flagged(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        flagged = db.get_needs_evidence_results(pid)
        assert len(flagged) == 0


# ═══════════════════════════════════════════════════════════════
# Enhanced Stats
# ═══════════════════════════════════════════════════════════════

class TestEnhancedStats:
    """REV-DB-STATS: Enhanced extraction stats tests."""

    def test_stats_include_confidence_distribution(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        stats = db.get_extraction_stats(pid)
        assert "confidence_distribution" in stats
        conf = stats["confidence_distribution"]
        assert "high" in conf
        assert "medium" in conf
        assert "low" in conf
        # High (>=0.8): description(0.95), founded_year(0.85) = 2
        assert conf["high"] == 2
        # Medium (0.5-0.8): headquarters(0.7), description(0.6) = 2
        assert conf["medium"] == 2
        # Low (<0.5): website_url(0.4), headquarters(0.3) = 2
        assert conf["low"] == 2

    def test_stats_include_needs_evidence_count(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        stats = db.get_extraction_stats(pid)
        assert "needs_evidence" in stats
        assert stats["needs_evidence"] == 0

        # Flag one
        db.flag_needs_evidence(review_db["result_ids"][0], needs=True)
        stats = db.get_extraction_stats(pid)
        assert stats["needs_evidence"] == 1

    def test_stats_include_entities_pending(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]
        stats = db.get_extraction_stats(pid)
        assert "entities_pending" in stats
        assert stats["entities_pending"] == 2

    def test_stats_entities_pending_decreases_after_review(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]

        # Accept all Acme Corp results
        for rid in review_db["result_ids"][:3]:
            db.review_extraction_result(rid, "accept")

        stats = db.get_extraction_stats(pid)
        assert stats["entities_pending"] == 1

    def test_stats_confidence_changes_after_review(self, review_db):
        db = review_db["db"]
        pid = review_db["project_id"]

        # Accept all high-confidence results
        db.review_extraction_result(review_db["result_ids"][0], "accept")  # 0.95
        db.review_extraction_result(review_db["result_ids"][2], "accept")  # 0.85

        stats = db.get_extraction_stats(pid)
        assert stats["confidence_distribution"]["high"] == 0

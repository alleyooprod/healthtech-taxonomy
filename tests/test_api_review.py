"""Tests for Human Review Interface — API layer.

Covers:
- GET  /api/extract/queue/grouped (grouped review queue with filters)
- POST /api/extract/results/<id>/flag (needs evidence flag)
- GET  /api/extract/needs-evidence (flagged results)
- Enhanced GET /api/extract/stats (confidence distribution, entities pending)
- Integration: review workflow end-to-end

Run: pytest tests/test_api_review.py -v
Markers: api, extraction
"""
import json
import pytest

pytestmark = [pytest.mark.api, pytest.mark.extraction]


# ═══════════════════════════════════════════════════════════════
# Schema + Fixtures
# ═══════════════════════════════════════════════════════════════

TEST_SCHEMA = {
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
def review_project(client):
    """Create a project with two entities and pending extraction results."""
    pid = client.db.create_project(
        name="Review API Test",
        purpose="Testing review API",
        entity_schema=TEST_SCHEMA,
    )
    e1 = client.db.create_entity(pid, "company", "AlphaCo")
    e2 = client.db.create_entity(pid, "company", "BravoCo")

    j1 = client.db.create_extraction_job(pid, e1, source_type="evidence")
    client.db.update_extraction_job(j1, status="completed")
    j2 = client.db.create_extraction_job(pid, e2, source_type="url", source_ref="https://bravo.com")
    client.db.update_extraction_job(j2, status="completed")

    # AlphaCo: high confidence
    r1 = client.db.create_extraction_result(j1, e1, "description", "Enterprise SaaS", confidence=0.92, reasoning="Homepage hero")
    r2 = client.db.create_extraction_result(j1, e1, "headquarters", "New York", confidence=0.88, reasoning="Footer address")

    # BravoCo: low confidence
    r3 = client.db.create_extraction_result(j2, e2, "description", "Some company", confidence=0.4, reasoning="Unclear")
    r4 = client.db.create_extraction_result(j2, e2, "website_url", "https://bravo.com", confidence=0.35, reasoning="Guessed from URL")

    return {
        "client": client,
        "project_id": pid,
        "entity_ids": [e1, e2],
        "job_ids": [j1, j2],
        "result_ids": [r1, r2, r3, r4],
    }


# ═══════════════════════════════════════════════════════════════
# Grouped Queue Endpoint
# ═══════════════════════════════════════════════════════════════

class TestGroupedQueueAPI:
    """REV-API-QUEUE: Grouped review queue endpoint tests."""

    def test_grouped_queue_returns_entities(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        r = c.get(f"/api/extract/queue/grouped?project_id={pid}")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 2
        names = {g["entity_name"] for g in data}
        assert "AlphaCo" in names
        assert "BravoCo" in names

    def test_grouped_queue_results_structure(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        r = c.get(f"/api/extract/queue/grouped?project_id={pid}")
        data = r.get_json()
        for group in data:
            assert "entity_id" in group
            assert "entity_name" in group
            assert "entity_type" in group
            assert "results" in group
            assert isinstance(group["results"], list)

    def test_grouped_queue_high_confidence_filter(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        r = c.get(f"/api/extract/queue/grouped?project_id={pid}&min_confidence=0.8")
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["entity_name"] == "AlphaCo"
        assert len(data[0]["results"]) == 2

    def test_grouped_queue_low_confidence_filter(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        r = c.get(f"/api/extract/queue/grouped?project_id={pid}&max_confidence=0.5")
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["entity_name"] == "BravoCo"

    def test_grouped_queue_entity_filter(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        e1 = review_project["entity_ids"][0]
        r = c.get(f"/api/extract/queue/grouped?project_id={pid}&entity_id={e1}")
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["entity_name"] == "AlphaCo"

    def test_grouped_queue_requires_project_id(self, review_project):
        c = review_project["client"]
        r = c.get("/api/extract/queue/grouped")
        assert r.status_code == 400

    def test_grouped_queue_empty_when_all_reviewed(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        # Accept all results
        for rid in review_project["result_ids"]:
            c.post(f"/api/extract/results/{rid}/review", json={"action": "accept"})
        r = c.get(f"/api/extract/queue/grouped?project_id={pid}")
        data = r.get_json()
        assert len(data) == 0


# ═══════════════════════════════════════════════════════════════
# Needs Evidence Flag Endpoint
# ═══════════════════════════════════════════════════════════════

class TestNeedsEvidenceAPI:
    """REV-API-FLAG: Needs evidence flag endpoint tests."""

    def test_flag_needs_evidence(self, review_project):
        c = review_project["client"]
        rid = review_project["result_ids"][0]
        r = c.post(f"/api/extract/results/{rid}/flag", json={"needs_evidence": True})
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "flagged"

    def test_unflag_needs_evidence(self, review_project):
        c = review_project["client"]
        rid = review_project["result_ids"][0]
        c.post(f"/api/extract/results/{rid}/flag", json={"needs_evidence": True})
        r = c.post(f"/api/extract/results/{rid}/flag", json={"needs_evidence": False})
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "unflagged"

    def test_flag_nonexistent_result(self, review_project):
        c = review_project["client"]
        r = c.post("/api/extract/results/99999/flag", json={"needs_evidence": True})
        assert r.status_code == 404

    def test_flag_defaults_to_true(self, review_project):
        c = review_project["client"]
        rid = review_project["result_ids"][0]
        r = c.post(f"/api/extract/results/{rid}/flag", json={})
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "flagged"

    def test_get_needs_evidence_results(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        rid = review_project["result_ids"][0]

        # Flag one result
        c.post(f"/api/extract/results/{rid}/flag", json={"needs_evidence": True})

        r = c.get(f"/api/extract/needs-evidence?project_id={pid}")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["id"] == rid

    def test_needs_evidence_requires_project_id(self, review_project):
        c = review_project["client"]
        r = c.get("/api/extract/needs-evidence")
        assert r.status_code == 400

    def test_needs_evidence_empty_when_none_flagged(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        r = c.get(f"/api/extract/needs-evidence?project_id={pid}")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 0


# ═══════════════════════════════════════════════════════════════
# Enhanced Stats
# ═══════════════════════════════════════════════════════════════

class TestEnhancedStatsAPI:
    """REV-API-STATS: Enhanced extraction stats endpoint tests."""

    def test_stats_include_confidence_distribution(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        r = c.get(f"/api/extract/stats?project_id={pid}")
        assert r.status_code == 200
        data = r.get_json()
        assert "confidence_distribution" in data
        conf = data["confidence_distribution"]
        assert conf["high"] == 2    # AlphaCo: 0.92, 0.88
        assert conf["medium"] == 0  # None in 0.5-0.8 range
        assert conf["low"] == 2     # BravoCo: 0.4, 0.35

    def test_stats_include_entities_pending(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        r = c.get(f"/api/extract/stats?project_id={pid}")
        data = r.get_json()
        assert data["entities_pending"] == 2

    def test_stats_include_needs_evidence(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]
        rid = review_project["result_ids"][0]

        c.post(f"/api/extract/results/{rid}/flag", json={"needs_evidence": True})

        r = c.get(f"/api/extract/stats?project_id={pid}")
        data = r.get_json()
        assert data["needs_evidence"] == 1

    def test_stats_update_after_review(self, review_project):
        c = review_project["client"]
        pid = review_project["project_id"]

        # Accept AlphaCo results
        c.post(f"/api/extract/results/{review_project['result_ids'][0]}/review",
               json={"action": "accept"})
        c.post(f"/api/extract/results/{review_project['result_ids'][1]}/review",
               json={"action": "accept"})

        r = c.get(f"/api/extract/stats?project_id={pid}")
        data = r.get_json()
        assert data["entities_pending"] == 1
        assert data["confidence_distribution"]["high"] == 0


# ═══════════════════════════════════════════════════════════════
# Integration: Full Review Workflow
# ═══════════════════════════════════════════════════════════════

class TestReviewWorkflow:
    """REV-API-FLOW: End-to-end review workflow tests."""

    def test_review_accept_writes_to_attributes(self, review_project):
        c = review_project["client"]
        rid = review_project["result_ids"][0]
        e1 = review_project["entity_ids"][0]

        # Accept description for AlphaCo
        r = c.post(f"/api/extract/results/{rid}/review", json={"action": "accept"})
        assert r.status_code == 200

        # Check entity attributes
        entity = c.db.get_entity(e1)
        attrs = entity.get("attributes", {})
        assert "description" in attrs
        assert attrs["description"]["value"] == "Enterprise SaaS"

    def test_review_edit_writes_edited_value(self, review_project):
        c = review_project["client"]
        rid = review_project["result_ids"][0]
        e1 = review_project["entity_ids"][0]

        r = c.post(f"/api/extract/results/{rid}/review",
                    json={"action": "edit", "edited_value": "Enterprise SaaS Platform"})
        assert r.status_code == 200

        entity = c.db.get_entity(e1)
        attrs = entity.get("attributes", {})
        assert attrs["description"]["value"] == "Enterprise SaaS Platform"

    def test_review_reject_does_not_write(self, review_project):
        c = review_project["client"]
        rid = review_project["result_ids"][0]
        e1 = review_project["entity_ids"][0]

        r = c.post(f"/api/extract/results/{rid}/review", json={"action": "reject"})
        assert r.status_code == 200

        entity = c.db.get_entity(e1)
        attrs = entity.get("attributes", {})
        assert "description" not in attrs

    def test_bulk_review_accept(self, review_project):
        c = review_project["client"]
        ids = review_project["result_ids"][:2]

        r = c.post("/api/extract/results/bulk-review",
                    json={"result_ids": ids, "action": "accept"})
        assert r.status_code == 200
        data = r.get_json()
        assert data["updated_count"] == 2

    def test_full_workflow_queue_to_empty(self, review_project):
        """Queue → review all → queue empty → stats updated."""
        c = review_project["client"]
        pid = review_project["project_id"]

        # Start: 4 pending, 2 entities
        r = c.get(f"/api/extract/stats?project_id={pid}")
        assert r.get_json()["pending_review"] == 4

        # Accept high-confidence (AlphaCo)
        c.post("/api/extract/results/bulk-review",
               json={"result_ids": review_project["result_ids"][:2], "action": "accept"})

        # Reject low-confidence (BravoCo)
        c.post("/api/extract/results/bulk-review",
               json={"result_ids": review_project["result_ids"][2:], "action": "reject"})

        # Queue should be empty
        r = c.get(f"/api/extract/queue/grouped?project_id={pid}")
        assert len(r.get_json()) == 0

        # Stats updated
        r = c.get(f"/api/extract/stats?project_id={pid}")
        stats = r.get_json()
        assert stats["pending_review"] == 0
        assert stats["entities_pending"] == 0

    def test_flag_then_review_workflow(self, review_project):
        """Flag as needing evidence, then eventually accept."""
        c = review_project["client"]
        pid = review_project["project_id"]
        rid = review_project["result_ids"][2]  # BravoCo low-confidence

        # Flag it
        c.post(f"/api/extract/results/{rid}/flag", json={"needs_evidence": True})
        r = c.get(f"/api/extract/needs-evidence?project_id={pid}")
        assert len(r.get_json()) == 1

        # Later, accept it despite flag
        r = c.post(f"/api/extract/results/{rid}/review", json={"action": "accept"})
        assert r.status_code == 200

        # No longer in pending queue
        r = c.get(f"/api/extract/queue/grouped?project_id={pid}")
        groups = r.get_json()
        for g in groups:
            for res in g["results"]:
                assert res["id"] != rid

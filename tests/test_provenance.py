"""Tests for Evidence Provenance API — tracing data points back to source evidence.

Covers:
- GET /api/provenance/attribute/<id>       — Trace single attribute
- GET /api/provenance/entity/<id>          — Entity provenance summary
- GET /api/provenance/entity/<id>/evidence — Reverse evidence map
- GET /api/provenance/project/<id>/coverage — Project-wide coverage
- GET /api/provenance/project/<id>/sources  — Unique source URLs
- GET /api/provenance/search               — Search attributes by value
- GET /api/provenance/report/<id>/claims   — Report claim->evidence links
- GET /api/provenance/stats                — Quick provenance stats
- Edge cases and graceful handling of missing tables

Run: pytest tests/test_provenance.py -v
Markers: api
"""
import json
import pytest

pytestmark = [pytest.mark.api]

# Schema used across tests
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
                {"name": "Pricing", "slug": "pricing", "data_type": "text"},
                {"name": "Founded Year", "slug": "founded_year", "data_type": "number"},
                {"name": "Headquarters", "slug": "headquarters", "data_type": "text"},
            ],
        },
    ],
    "relationships": [],
}


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _create_project(client, name="Provenance Test"):
    """Create a project and return its ID."""
    return client.db.create_project(
        name=name,
        purpose="Testing provenance API",
        entity_schema=TEST_SCHEMA,
    )


def _create_entity(client, project_id, name="TestCo", type_slug="company"):
    """Create an entity and return its ID."""
    return client.db.create_entity(project_id, type_slug, name)


def _set_attribute(client, entity_id, attr_slug, value,
                   source="manual", confidence=None, captured_at=None):
    """Set an attribute on an entity and return the attr ID."""
    client.db.set_entity_attribute(
        entity_id, attr_slug, value,
        source=source, confidence=confidence,
        captured_at=captured_at,
    )
    # Fetch the ID of the attribute we just set
    with client.db._get_conn() as conn:
        row = conn.execute(
            """SELECT id FROM entity_attributes
               WHERE entity_id = ? AND attr_slug = ?
               ORDER BY id DESC LIMIT 1""",
            (entity_id, attr_slug),
        ).fetchone()
        return row["id"]


def _add_evidence(client, entity_id, evidence_type="page_archive",
                  file_path="/some/path/page.html",
                  source_url="https://example.com/product",
                  source_name="Product Page"):
    """Add evidence to an entity and return its ID."""
    return client.db.add_evidence(
        entity_id=entity_id,
        evidence_type=evidence_type,
        file_path=file_path,
        source_url=source_url,
        source_name=source_name,
    )


def _setup_extraction_chain(client, entity_id, project_id,
                            attr_slug="pricing", value="$99/mo",
                            source_url="https://example.com/product"):
    """Create a full extraction chain: evidence -> job -> result -> attribute.

    Returns dict with evidence_id, job_id, result_id, attr_id.
    """
    # Insert evidence
    evidence_id = _add_evidence(
        client, entity_id,
        evidence_type="page_archive",
        file_path=f"/evidence/{project_id}/{entity_id}/page_archive/page.html",
        source_url=source_url,
        source_name="Product Page",
    )

    with client.db._get_conn() as conn:
        # Insert extraction job
        conn.execute(
            """INSERT INTO extraction_jobs
               (project_id, entity_id, evidence_id, source_type,
                source_ref, model, status)
               VALUES (?, ?, ?, 'product_page', ?, 'claude-sonnet', 'completed')""",
            (project_id, entity_id, evidence_id, source_url),
        )
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Insert extraction result (accepted)
        conn.execute(
            """INSERT INTO extraction_results
               (job_id, entity_id, attr_slug, extracted_value, confidence,
                status, source_evidence_id, created_at)
               VALUES (?, ?, ?, ?, 0.9, 'accepted', ?, '2026-02-10 10:01:00')""",
            (job_id, entity_id, attr_slug, value, evidence_id),
        )
        result_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Insert entity attribute with source='extraction'
        conn.execute(
            """INSERT INTO entity_attributes
               (entity_id, attr_slug, value, source, confidence, captured_at)
               VALUES (?, ?, ?, 'extraction', 0.9, '2026-02-10 10:01:00')""",
            (entity_id, attr_slug, value),
        )
        attr_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.commit()

    return {
        "evidence_id": evidence_id,
        "job_id": job_id,
        "result_id": result_id,
        "attr_id": attr_id,
    }


# ═══════════════════════════════════════════════════════════════
# 1. Trace Single Attribute
# ═══════════════════════════════════════════════════════════════

class TestAttributeTrace:
    """PROV-AT: Trace single attribute provenance chain."""

    def test_manual_source_chain(self, client):
        """Manual attribute has chain ["attribute", "manual"]."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        attr_id = _set_attribute(client, eid, "description", "A test company")

        resp = client.get(f"/api/provenance/attribute/{attr_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["chain"] == ["attribute", "manual"]
        assert data["extraction"] is None
        assert data["evidence"] is None
        assert data["source_url"] is None

    def test_sync_source_chain(self, client):
        """Sync attribute has chain ["attribute", "sync"]."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        attr_id = _set_attribute(client, eid, "description", "Synced value",
                                 source="sync")

        resp = client.get(f"/api/provenance/attribute/{attr_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["chain"] == ["attribute", "sync"]

    def test_null_source_treated_as_manual(self, client):
        """Attribute with NULL source treated as manual."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        # Insert attribute with NULL source directly
        with client.db._get_conn() as conn:
            conn.execute(
                """INSERT INTO entity_attributes
                   (entity_id, attr_slug, value, source, captured_at)
                   VALUES (?, 'description', 'No source', NULL, datetime('now'))""",
                (eid,),
            )
            attr_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()

        resp = client.get(f"/api/provenance/attribute/{attr_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["chain"] == ["attribute", "manual"]

    def test_extraction_full_chain(self, client):
        """Extraction with evidence and URL has chain
        ["attribute", "extraction", "evidence", "url"]."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        chain = _setup_extraction_chain(client, eid, pid)

        resp = client.get(f"/api/provenance/attribute/{chain['attr_id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["chain"] == ["attribute", "extraction", "evidence", "url"]
        assert data["source_url"] == "https://example.com/product"
        assert data["extraction"] is not None
        assert data["extraction"]["result_id"] == chain["result_id"]
        assert data["extraction"]["job_id"] == chain["job_id"]
        assert data["extraction"]["extractor_type"] == "product_page"
        assert data["evidence"] is not None
        assert data["evidence"]["id"] == chain["evidence_id"]
        assert data["evidence"]["evidence_type"] == "page_archive"

    def test_extraction_without_evidence(self, client):
        """Extraction result with no linked evidence has chain
        ["attribute", "extraction"]."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        with client.db._get_conn() as conn:
            # Job without evidence_id
            conn.execute(
                """INSERT INTO extraction_jobs
                   (project_id, entity_id, evidence_id, source_type,
                    source_ref, model, status)
                   VALUES (?, ?, NULL, 'url', 'https://example.com', 'claude-sonnet',
                           'completed')""",
                (pid, eid),
            )
            job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Result without source_evidence_id
            conn.execute(
                """INSERT INTO extraction_results
                   (job_id, entity_id, attr_slug, extracted_value, confidence,
                    status, source_evidence_id, created_at)
                   VALUES (?, ?, 'pricing', '$49/mo', 0.8, 'accepted', NULL,
                           '2026-02-10 10:01:00')""",
                (job_id, eid),
            )

            # Attribute with extraction source
            conn.execute(
                """INSERT INTO entity_attributes
                   (entity_id, attr_slug, value, source, confidence, captured_at)
                   VALUES (?, 'pricing', '$49/mo', 'extraction', 0.8,
                           '2026-02-10 10:01:00')""",
                (eid,),
            )
            attr_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()

        resp = client.get(f"/api/provenance/attribute/{attr_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["chain"] == ["attribute", "extraction"]
        assert data["extraction"] is not None
        assert data["evidence"] is None
        assert data["source_url"] is None

    def test_attribute_not_found(self, client):
        """Non-existent attribute returns 404."""
        resp = client.get("/api/provenance/attribute/99999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "not found" in data["error"].lower()

    def test_response_structure(self, client):
        """Response has all expected top-level fields."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        attr_id = _set_attribute(client, eid, "description", "Some value")

        resp = client.get(f"/api/provenance/attribute/{attr_id}")
        assert resp.status_code == 200
        data = resp.get_json()

        assert "attribute" in data
        assert "extraction" in data
        assert "evidence" in data
        assert "chain" in data
        assert "source_url" in data

        # Attribute sub-fields
        attr = data["attribute"]
        assert "id" in attr
        assert "entity_id" in attr
        assert "attr_slug" in attr
        assert "value" in attr
        assert "source" in attr

    def test_extraction_fallback_to_job_evidence_id(self, client):
        """When result has no source_evidence_id, falls back to job's evidence_id."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        evidence_id = _add_evidence(client, eid)

        with client.db._get_conn() as conn:
            # Job WITH evidence_id
            conn.execute(
                """INSERT INTO extraction_jobs
                   (project_id, entity_id, evidence_id, source_type,
                    source_ref, model, status)
                   VALUES (?, ?, ?, 'product_page', 'https://example.com/product',
                           'claude-sonnet', 'completed')""",
                (pid, eid, evidence_id),
            )
            job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Result WITHOUT source_evidence_id
            conn.execute(
                """INSERT INTO extraction_results
                   (job_id, entity_id, attr_slug, extracted_value, confidence,
                    status, source_evidence_id, created_at)
                   VALUES (?, ?, 'pricing', '$79/mo', 0.85, 'accepted', NULL,
                           '2026-02-10 10:01:00')""",
                (job_id, eid),
            )

            # Attribute
            conn.execute(
                """INSERT INTO entity_attributes
                   (entity_id, attr_slug, value, source, confidence, captured_at)
                   VALUES (?, 'pricing', '$79/mo', 'extraction', 0.85,
                           '2026-02-10 10:01:00')""",
                (eid,),
            )
            attr_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()

        resp = client.get(f"/api/provenance/attribute/{attr_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        # Should get evidence via fallback to job's evidence_id
        assert data["evidence"] is not None
        assert data["evidence"]["id"] == evidence_id
        assert data["chain"] == ["attribute", "extraction", "evidence", "url"]

    def test_extraction_evidence_without_url(self, client):
        """Evidence without source_url gives chain without 'url'."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        # Evidence without source_url
        evidence_id = _add_evidence(client, eid, source_url=None)

        with client.db._get_conn() as conn:
            conn.execute(
                """INSERT INTO extraction_jobs
                   (project_id, entity_id, evidence_id, source_type,
                    source_ref, model, status)
                   VALUES (?, ?, ?, 'product_page', NULL, 'claude-sonnet',
                           'completed')""",
                (pid, eid, evidence_id),
            )
            job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            conn.execute(
                """INSERT INTO extraction_results
                   (job_id, entity_id, attr_slug, extracted_value, confidence,
                    status, source_evidence_id, created_at)
                   VALUES (?, ?, 'pricing', '$59/mo', 0.7, 'accepted', ?,
                           '2026-02-10 10:01:00')""",
                (job_id, eid, evidence_id),
            )

            conn.execute(
                """INSERT INTO entity_attributes
                   (entity_id, attr_slug, value, source, confidence, captured_at)
                   VALUES (?, 'pricing', '$59/mo', 'extraction', 0.7,
                           '2026-02-10 10:01:00')""",
                (eid,),
            )
            attr_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()

        resp = client.get(f"/api/provenance/attribute/{attr_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["chain"] == ["attribute", "extraction", "evidence"]
        assert data["source_url"] is None
        assert data["evidence"] is not None


# ═══════════════════════════════════════════════════════════════
# 2. Entity Provenance Summary
# ═══════════════════════════════════════════════════════════════

class TestEntityProvenance:
    """PROV-EP: Entity provenance summary."""

    def test_entity_no_attributes(self, client):
        """Entity with no attributes returns empty list and 0 coverage."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        resp = client.get(f"/api/provenance/entity/{eid}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["entity_id"] == eid
        assert data["entity_name"] == "TestCo"
        assert data["attributes"] == []
        assert data["coverage"]["total"] == 0
        assert data["coverage"]["coverage_pct"] == 0.0

    def test_entity_mixed_sources(self, client):
        """Entity with manual + extraction attributes has correct provenance."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        # Manual attribute
        _set_attribute(client, eid, "description", "A test company")

        # Extraction attribute with full chain
        _setup_extraction_chain(client, eid, pid)

        resp = client.get(f"/api/provenance/entity/{eid}")
        assert resp.status_code == 200
        data = resp.get_json()

        assert len(data["attributes"]) == 2
        attr_by_slug = {a["attr_slug"]: a for a in data["attributes"]}

        desc = attr_by_slug["description"]
        assert desc["source"] == "manual"
        assert desc["has_evidence"] is False
        assert desc["chain_length"] == 1

        pricing = attr_by_slug["pricing"]
        assert pricing["source"] == "extraction"
        assert pricing["has_evidence"] is True
        assert pricing["source_url"] == "https://example.com/product"
        assert pricing["chain_length"] == 4

    def test_coverage_calculation(self, client):
        """Coverage percentages are calculated correctly."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        # 1 manual + 1 extraction-backed = 50% coverage
        _set_attribute(client, eid, "description", "Manual value")
        _setup_extraction_chain(client, eid, pid)

        resp = client.get(f"/api/provenance/entity/{eid}")
        data = resp.get_json()

        assert data["coverage"]["total"] == 2
        assert data["coverage"]["with_evidence"] == 1
        assert data["coverage"]["without_evidence"] == 1
        assert data["coverage"]["coverage_pct"] == 50.0

    def test_entity_not_found(self, client):
        """Non-existent entity returns 404."""
        resp = client.get("/api/provenance/entity/99999")
        assert resp.status_code == 404

    def test_deleted_entity_not_found(self, client):
        """Deleted entity returns 404."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        # Soft-delete the entity
        with client.db._get_conn() as conn:
            conn.execute(
                "UPDATE entities SET is_deleted = 1 WHERE id = ?", (eid,)
            )
            conn.commit()

        resp = client.get(f"/api/provenance/entity/{eid}")
        assert resp.status_code == 404

    def test_chain_length_manual_is_one(self, client):
        """Manual attributes have chain_length 1."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _set_attribute(client, eid, "description", "Manual")

        resp = client.get(f"/api/provenance/entity/{eid}")
        data = resp.get_json()
        assert data["attributes"][0]["chain_length"] == 1

    def test_response_structure(self, client):
        """Response has all expected fields."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        resp = client.get(f"/api/provenance/entity/{eid}")
        data = resp.get_json()

        assert "entity_id" in data
        assert "entity_name" in data
        assert "attributes" in data
        assert "coverage" in data
        cov = data["coverage"]
        assert "total" in cov
        assert "with_evidence" in cov
        assert "without_evidence" in cov
        assert "coverage_pct" in cov


# ═══════════════════════════════════════════════════════════════
# 3. Entity Evidence Map
# ═══════════════════════════════════════════════════════════════

class TestEntityEvidenceMap:
    """PROV-EM: Reverse evidence map for an entity."""

    def test_entity_no_evidence(self, client):
        """Entity with no evidence returns empty list."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        resp = client.get(f"/api/provenance/entity/{eid}/evidence")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["entity_id"] == eid
        assert data["evidence"] == []

    def test_evidence_with_linked_extraction_results(self, client):
        """Evidence with extraction results shows supported_attributes."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        chain = _setup_extraction_chain(client, eid, pid)

        resp = client.get(f"/api/provenance/entity/{eid}/evidence")
        assert resp.status_code == 200
        data = resp.get_json()

        assert len(data["evidence"]) == 1
        ev = data["evidence"][0]
        assert ev["id"] == chain["evidence_id"]
        assert ev["type"] == "page_archive"
        assert ev["url"] == "https://example.com/product"
        assert len(ev["supported_attributes"]) == 1
        assert ev["supported_attributes"][0]["slug"] == "pricing"
        assert ev["supported_attributes"][0]["value"] == "$99/mo"

    def test_evidence_fields(self, client):
        """Evidence entry has all expected fields."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _add_evidence(client, eid)

        resp = client.get(f"/api/provenance/entity/{eid}/evidence")
        data = resp.get_json()

        assert len(data["evidence"]) == 1
        ev = data["evidence"][0]
        assert "id" in ev
        assert "type" in ev
        assert "filename" in ev
        assert "url" in ev
        assert "captured_at" in ev
        assert "supported_attributes" in ev

    def test_evidence_filename_extracted(self, client):
        """Filename is extracted from file_path."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _add_evidence(client, eid, file_path="/some/nested/path/screenshot.png")

        resp = client.get(f"/api/provenance/entity/{eid}/evidence")
        data = resp.get_json()
        assert data["evidence"][0]["filename"] == "screenshot.png"

    def test_entity_not_found(self, client):
        """Non-existent entity returns 404."""
        resp = client.get("/api/provenance/entity/99999/evidence")
        assert resp.status_code == 404

    def test_multiple_evidence_items(self, client):
        """Entity with multiple evidence items returns all."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _add_evidence(client, eid, evidence_type="page_archive",
                      source_url="https://example.com/about")
        _add_evidence(client, eid, evidence_type="screenshot",
                      file_path="/path/screenshot.png",
                      source_url="https://example.com/pricing")

        resp = client.get(f"/api/provenance/entity/{eid}/evidence")
        data = resp.get_json()
        assert len(data["evidence"]) == 2


# ═══════════════════════════════════════════════════════════════
# 4. Project Coverage
# ═══════════════════════════════════════════════════════════════

class TestProjectCoverage:
    """PROV-PC: Project-wide provenance coverage."""

    def test_empty_project(self, client):
        """Project with no entities has 0 coverage."""
        pid = _create_project(client)

        resp = client.get(f"/api/provenance/project/{pid}/coverage")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["project_id"] == pid
        assert data["total_attributes"] == 0
        assert data["with_evidence"] == 0
        assert data["coverage_pct"] == 0.0
        assert data["entities"] == []

    def test_project_mixed_coverage(self, client):
        """Project with entities having mixed sources."""
        pid = _create_project(client)

        # Entity 1: manual attribute only
        eid1 = _create_entity(client, pid, name="ManualCo")
        _set_attribute(client, eid1, "description", "Manual description")

        # Entity 2: extraction-backed attribute
        eid2 = _create_entity(client, pid, name="ExtractedCo")
        _setup_extraction_chain(client, eid2, pid)

        resp = client.get(f"/api/provenance/project/{pid}/coverage")
        data = resp.get_json()

        assert data["total_attributes"] == 2
        assert data["with_evidence"] == 1
        assert data["manual_only"] == 1
        assert data["with_extraction"] == 1
        assert data["coverage_pct"] == 50.0

        # Check entity summaries
        assert len(data["entities"]) == 2
        ent_by_name = {e["name"]: e for e in data["entities"]}

        manual = ent_by_name["ManualCo"]
        assert manual["total_attrs"] == 1
        assert manual["evidence_backed"] == 0
        assert manual["pct"] == 0.0

        extracted = ent_by_name["ExtractedCo"]
        assert extracted["total_attrs"] == 1
        assert extracted["evidence_backed"] == 1
        assert extracted["pct"] == 100.0

    def test_project_not_found(self, client):
        """Non-existent project returns 404."""
        resp = client.get("/api/provenance/project/99999/coverage")
        assert resp.status_code == 404

    def test_coverage_pct_calculation(self, client):
        """Coverage percentage computed correctly with 3 attrs, 1 evidence-backed."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        _set_attribute(client, eid, "description", "Manual")
        _set_attribute(client, eid, "headquarters", "London")
        _setup_extraction_chain(client, eid, pid)

        resp = client.get(f"/api/provenance/project/{pid}/coverage")
        data = resp.get_json()

        assert data["total_attributes"] == 3
        assert data["with_evidence"] == 1
        assert data["manual_only"] == 2
        # 1/3 = 33.3%
        assert data["coverage_pct"] == 33.3

    def test_entity_summaries_present(self, client):
        """Entity summaries contain correct fields."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _set_attribute(client, eid, "description", "Test")

        resp = client.get(f"/api/provenance/project/{pid}/coverage")
        data = resp.get_json()

        assert len(data["entities"]) == 1
        ent = data["entities"][0]
        assert ent["id"] == eid
        assert ent["name"] == "TestCo"
        assert "total_attrs" in ent
        assert "evidence_backed" in ent
        assert "pct" in ent


# ═══════════════════════════════════════════════════════════════
# 5. Project Sources
# ═══════════════════════════════════════════════════════════════

class TestProjectSources:
    """PROV-PS: Unique source URLs across a project."""

    def test_empty_project(self, client):
        """Project with no evidence has no sources."""
        pid = _create_project(client)

        resp = client.get(f"/api/provenance/project/{pid}/sources")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["project_id"] == pid
        assert data["sources"] == []
        assert data["total_sources"] == 0

    def test_project_with_evidence_urls(self, client):
        """Project sources list evidence URLs."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _add_evidence(client, eid, source_url="https://acme.com/about")
        _add_evidence(client, eid, source_url="https://acme.com/pricing",
                      evidence_type="screenshot",
                      file_path="/path/pricing.png")

        resp = client.get(f"/api/provenance/project/{pid}/sources")
        data = resp.get_json()

        assert data["total_sources"] == 2
        urls = [s["url"] for s in data["sources"]]
        assert "https://acme.com/about" in urls
        assert "https://acme.com/pricing" in urls

    def test_sources_sorted_by_url(self, client):
        """Sources sorted alphabetically by URL."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _add_evidence(client, eid, source_url="https://zebra.com")
        _add_evidence(client, eid, source_url="https://alpha.com",
                      file_path="/p/a.html")

        resp = client.get(f"/api/provenance/project/{pid}/sources")
        data = resp.get_json()

        urls = [s["url"] for s in data["sources"]]
        assert urls == sorted(urls)

    def test_entity_count_and_evidence_types(self, client):
        """Sources show entity count and evidence types."""
        pid = _create_project(client)
        eid1 = _create_entity(client, pid, name="Co1")
        eid2 = _create_entity(client, pid, name="Co2")

        url = "https://shared-source.com"
        _add_evidence(client, eid1, source_url=url, evidence_type="page_archive")
        _add_evidence(client, eid2, source_url=url, evidence_type="screenshot",
                      file_path="/p/ss.png")

        resp = client.get(f"/api/provenance/project/{pid}/sources")
        data = resp.get_json()

        assert data["total_sources"] == 1
        src = data["sources"][0]
        assert src["url"] == url
        assert src["entity_count"] == 2
        assert set(src["evidence_types"]) == {"page_archive", "screenshot"}

    def test_project_not_found(self, client):
        """Non-existent project returns 404."""
        resp = client.get("/api/provenance/project/99999/sources")
        assert resp.status_code == 404

    def test_null_url_excluded(self, client):
        """Evidence with NULL source_url excluded from sources."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _add_evidence(client, eid, source_url=None)
        _add_evidence(client, eid, source_url="https://real-url.com",
                      file_path="/p/b.html")

        resp = client.get(f"/api/provenance/project/{pid}/sources")
        data = resp.get_json()

        assert data["total_sources"] == 1
        assert data["sources"][0]["url"] == "https://real-url.com"


# ═══════════════════════════════════════════════════════════════
# 6. Search Attributes by Value
# ═══════════════════════════════════════════════════════════════

class TestProvenanceSearch:
    """PROV-SR: Search attributes by value with provenance info."""

    def test_basic_text_search(self, client):
        """Search finds attributes matching the query term."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _set_attribute(client, eid, "description", "Enterprise SaaS platform")
        _set_attribute(client, eid, "headquarters", "London")

        resp = client.get(f"/api/provenance/search?project_id={pid}&q=SaaS")
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["total"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["attr_slug"] == "description"
        assert data["results"][0]["entity_name"] == "TestCo"

    def test_search_with_attr_slug_filter(self, client):
        """Search with attr_slug limits to specific attribute."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _set_attribute(client, eid, "description", "Premium pricing available")
        _set_attribute(client, eid, "pricing", "Premium: $199/mo")

        # Search for "Premium" but filter to pricing only
        resp = client.get(
            f"/api/provenance/search?project_id={pid}&q=Premium&attr_slug=pricing"
        )
        data = resp.get_json()

        assert data["total"] == 1
        assert data["results"][0]["attr_slug"] == "pricing"

    def test_pagination(self, client):
        """Limit and offset pagination works."""
        pid = _create_project(client)
        for i in range(5):
            eid = _create_entity(client, pid, name=f"Company{i}")
            _set_attribute(client, eid, "description", f"Test company {i}")

        # First page (limit=2)
        resp = client.get(
            f"/api/provenance/search?project_id={pid}&q=Test&limit=2&offset=0"
        )
        data = resp.get_json()
        assert len(data["results"]) == 2
        assert data["total"] == 5

        # Second page
        resp = client.get(
            f"/api/provenance/search?project_id={pid}&q=Test&limit=2&offset=2"
        )
        data = resp.get_json()
        assert len(data["results"]) == 2
        assert data["total"] == 5

    def test_project_id_required(self, client):
        """Missing project_id returns 400."""
        resp = client.get("/api/provenance/search?q=test")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "project_id" in data["error"].lower()

    def test_q_required(self, client):
        """Missing q parameter returns 400."""
        pid = _create_project(client)
        resp = client.get(f"/api/provenance/search?project_id={pid}")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "q" in data["error"].lower()

    def test_empty_results(self, client):
        """Search with no matches returns empty results."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _set_attribute(client, eid, "description", "A company")

        resp = client.get(
            f"/api/provenance/search?project_id={pid}&q=zzzznonexistent"
        )
        data = resp.get_json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_chain_length_in_results(self, client):
        """Search results include chain_length and evidence_url."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _set_attribute(client, eid, "description", "Manual value")
        _setup_extraction_chain(client, eid, pid, value="$99/mo from extraction")

        # Search for manual value
        resp = client.get(
            f"/api/provenance/search?project_id={pid}&q=Manual"
        )
        data = resp.get_json()
        assert data["results"][0]["chain_length"] == 1
        assert data["results"][0]["evidence_url"] is None

    def test_extraction_evidence_url_in_results(self, client):
        """Search results show evidence_url for extraction-backed attributes."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _setup_extraction_chain(client, eid, pid, value="$99/mo",
                                source_url="https://example.com/pricing")

        resp = client.get(
            f"/api/provenance/search?project_id={pid}&q=99"
        )
        data = resp.get_json()
        assert len(data["results"]) == 1
        assert data["results"][0]["evidence_url"] == "https://example.com/pricing"
        assert data["results"][0]["chain_length"] == 4


# ═══════════════════════════════════════════════════════════════
# 7. Report Claims -> Evidence
# ═══════════════════════════════════════════════════════════════

class TestReportClaims:
    """PROV-RC: Report claim -> evidence links."""

    def _create_reports_table(self, client):
        """Create workbench_reports table for testing."""
        with client.db._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workbench_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content_json TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.commit()

    def _insert_report(self, client, project_id, title, sections):
        """Insert a report and return its ID."""
        content = json.dumps({"sections": sections})
        with client.db._get_conn() as conn:
            conn.execute(
                """INSERT INTO workbench_reports (project_id, title, content_json)
                   VALUES (?, ?, ?)""",
                (project_id, title, content),
            )
            report_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
            return report_id

    def test_report_with_entity_references(self, client):
        """Report section referencing entity name found in claims."""
        self._create_reports_table(client)
        pid = _create_project(client)
        eid = _create_entity(client, pid, name="AcmeCorp")
        _set_attribute(client, eid, "description", "Enterprise platform")

        report_id = self._insert_report(client, pid, "Market Report", [
            {"heading": "Overview", "content": "AcmeCorp is a leading player."},
        ])

        resp = client.get(
            f"/api/provenance/report/{report_id}/claims?project_id={pid}"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["report_id"] == report_id
        assert len(data["claims"]) == 1
        assert "AcmeCorp" in data["claims"][0]["referenced_entities"]

    def test_report_with_value_references(self, client):
        """Report referencing attribute values gets evidence_url."""
        self._create_reports_table(client)
        pid = _create_project(client)
        eid = _create_entity(client, pid, name="AcmeCorp")

        chain = _setup_extraction_chain(
            client, eid, pid,
            attr_slug="pricing", value="$99/mo",
            source_url="https://acme.com/pricing",
        )

        report_id = self._insert_report(client, pid, "Pricing Report", [
            {"heading": "Pricing Analysis",
             "content": "AcmeCorp charges $99/mo for their enterprise plan."},
        ])

        resp = client.get(
            f"/api/provenance/report/{report_id}/claims?project_id={pid}"
        )
        data = resp.get_json()
        assert len(data["claims"]) == 1
        claim = data["claims"][0]
        assert "AcmeCorp" in claim["referenced_entities"]
        assert len(claim["referenced_values"]) >= 1

        pricing_ref = [v for v in claim["referenced_values"]
                       if v["attr"] == "pricing"]
        assert len(pricing_ref) == 1
        assert pricing_ref[0]["evidence_url"] == "https://acme.com/pricing"

    def test_report_not_found(self, client):
        """Non-existent report returns 404."""
        self._create_reports_table(client)
        pid = _create_project(client)

        resp = client.get(
            f"/api/provenance/report/99999/claims?project_id={pid}"
        )
        assert resp.status_code == 404

    def test_reports_table_missing(self, client):
        """Missing workbench_reports table returns 404."""
        pid = _create_project(client)
        resp = client.get(
            f"/api/provenance/report/1/claims?project_id={pid}"
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert "not found" in data["error"].lower()

    def test_project_id_required(self, client):
        """Missing project_id returns 400."""
        resp = client.get("/api/provenance/report/1/claims")
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════
# 8. Quick Provenance Stats
# ═══════════════════════════════════════════════════════════════

class TestProvenanceStats:
    """PROV-ST: Quick provenance statistics."""

    def test_empty_project(self, client):
        """Empty project has zero stats."""
        pid = _create_project(client)

        resp = client.get(f"/api/provenance/stats?project_id={pid}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_attributes"] == 0
        assert data["evidence_backed"] == 0
        assert data["extraction_backed"] == 0
        assert data["manual_only"] == 0
        assert data["sync_only"] == 0
        assert data["coverage_pct"] == 0.0
        assert data["source_count"] == 0
        assert data["evidence_count"] == 0

    def test_mixed_sources(self, client):
        """Project with mixed attribute sources has correct counts."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        _set_attribute(client, eid, "description", "Manual desc")
        _set_attribute(client, eid, "headquarters", "London", source="sync")
        _setup_extraction_chain(client, eid, pid)

        resp = client.get(f"/api/provenance/stats?project_id={pid}")
        data = resp.get_json()

        assert data["total_attributes"] == 3
        assert data["manual_only"] == 1
        assert data["sync_only"] == 1
        assert data["extraction_backed"] == 1
        assert data["evidence_backed"] == 1
        assert data["evidence_count"] == 1
        assert data["source_count"] == 1

    def test_all_fields_present(self, client):
        """Response contains all expected stat fields."""
        pid = _create_project(client)

        resp = client.get(f"/api/provenance/stats?project_id={pid}")
        data = resp.get_json()

        expected_keys = {
            "total_attributes", "evidence_backed", "extraction_backed",
            "manual_only", "sync_only", "coverage_pct",
            "source_count", "evidence_count",
        }
        assert expected_keys.issubset(set(data.keys()))

    def test_project_id_required(self, client):
        """Missing project_id returns 400."""
        resp = client.get("/api/provenance/stats")
        assert resp.status_code == 400

    def test_project_not_found(self, client):
        """Non-existent project returns 404."""
        resp = client.get("/api/provenance/stats?project_id=99999")
        assert resp.status_code == 404

    def test_evidence_and_source_counts(self, client):
        """Multiple evidence items counted correctly."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        _add_evidence(client, eid, source_url="https://a.com")
        _add_evidence(client, eid, source_url="https://b.com",
                      file_path="/p/b.html")
        _add_evidence(client, eid, source_url="https://a.com",
                      file_path="/p/a2.html",
                      evidence_type="screenshot")

        resp = client.get(f"/api/provenance/stats?project_id={pid}")
        data = resp.get_json()

        assert data["evidence_count"] == 3
        assert data["source_count"] == 2  # 2 distinct URLs


# ═══════════════════════════════════════════════════════════════
# 9. Edge Cases
# ═══════════════════════════════════════════════════════════════

class TestProvenanceEdgeCases:
    """PROV-EC: Edge cases and graceful error handling."""

    def test_entity_only_sync_attributes(self, client):
        """Entity with only sync attributes has 0 evidence coverage."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _set_attribute(client, eid, "description", "Synced desc", source="sync")
        _set_attribute(client, eid, "headquarters", "NYC", source="sync")

        resp = client.get(f"/api/provenance/entity/{eid}")
        data = resp.get_json()
        assert data["coverage"]["with_evidence"] == 0
        assert data["coverage"]["coverage_pct"] == 0.0

    def test_attribute_with_extraction_source_no_matching_result(self, client):
        """Attribute marked as 'extraction' but no matching extraction_result
        in the DB produces chain ["attribute", "extraction"]."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)

        with client.db._get_conn() as conn:
            conn.execute(
                """INSERT INTO entity_attributes
                   (entity_id, attr_slug, value, source, confidence, captured_at)
                   VALUES (?, 'pricing', 'orphaned', 'extraction', 0.5,
                           '2026-02-10 10:00:00')""",
                (eid,),
            )
            attr_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()

        resp = client.get(f"/api/provenance/attribute/{attr_id}")
        data = resp.get_json()
        assert data["chain"] == ["attribute", "extraction"]
        assert data["extraction"] is None

    def test_search_case_insensitive(self, client):
        """Search is case-insensitive (LIKE is case-insensitive for ASCII in SQLite)."""
        pid = _create_project(client)
        eid = _create_entity(client, pid)
        _set_attribute(client, eid, "description", "ENTERPRISE Platform")

        resp = client.get(
            f"/api/provenance/search?project_id={pid}&q=enterprise"
        )
        data = resp.get_json()
        assert data["total"] == 1

    def test_multiple_entities_in_report(self, client):
        """Report section referencing multiple entities finds all."""
        with client.db._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workbench_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content_json TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.commit()

        pid = _create_project(client)
        _create_entity(client, pid, name="AlphaCo")
        _create_entity(client, pid, name="BetaCo")

        content = json.dumps({"sections": [
            {"heading": "Comparison",
             "content": "AlphaCo and BetaCo compete in the same market."},
        ]})
        with client.db._get_conn() as conn:
            conn.execute(
                """INSERT INTO workbench_reports (project_id, title, content_json)
                   VALUES (?, 'Comparison', ?)""",
                (pid, content),
            )
            report_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()

        resp = client.get(
            f"/api/provenance/report/{report_id}/claims?project_id={pid}"
        )
        data = resp.get_json()
        assert len(data["claims"]) == 1
        entities = data["claims"][0]["referenced_entities"]
        assert "AlphaCo" in entities
        assert "BetaCo" in entities

    def test_coverage_with_deleted_entity_excluded(self, client):
        """Deleted entities excluded from project coverage."""
        pid = _create_project(client)
        eid1 = _create_entity(client, pid, name="ActiveCo")
        eid2 = _create_entity(client, pid, name="DeletedCo")

        _set_attribute(client, eid1, "description", "Active")
        _set_attribute(client, eid2, "description", "Deleted")

        # Soft-delete entity 2
        with client.db._get_conn() as conn:
            conn.execute(
                "UPDATE entities SET is_deleted = 1 WHERE id = ?", (eid2,)
            )
            conn.commit()

        resp = client.get(f"/api/provenance/project/{pid}/coverage")
        data = resp.get_json()

        # Only active entity's attributes counted
        assert data["total_attributes"] == 1
        assert len(data["entities"]) == 1
        assert data["entities"][0]["name"] == "ActiveCo"

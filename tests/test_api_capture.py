"""Tests for Capture API — website capture, document download, evidence upload/serve.

Covers:
- POST /api/capture/website (mocked Playwright)
- POST /api/capture/document (mocked HTTP)
- POST /api/evidence/upload (multipart file upload)
- GET  /api/evidence/<id>/file (serve evidence file)
- DELETE /api/evidence/<id>/file (delete file + record)
- GET  /api/evidence/stats (storage statistics)
- GET  /api/capture/jobs (background job listing)
- Validation: missing fields, invalid entity, bad file types

Run: pytest tests/test_api_capture.py -v
Markers: api, capture
"""
import io
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from core.capture import CaptureResult

pytestmark = [pytest.mark.api, pytest.mark.capture]

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
                {"name": "URL", "slug": "url", "data_type": "url"},
            ],
        },
    ],
    "relationships": [],
}


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def capture_project(client, tmp_path, monkeypatch):
    """Create a project with entity, redirect evidence dir to tmp."""
    import core.capture as capture_mod
    test_evidence_dir = tmp_path / "evidence"
    test_evidence_dir.mkdir()
    monkeypatch.setattr(capture_mod, "EVIDENCE_DIR", test_evidence_dir)

    pid = client.db.create_project(
        name="Capture API Test",
        purpose="Testing capture API",
        entity_schema=TEST_SCHEMA,
    )
    eid = client.db.create_entity(pid, "company", "TestCo")
    return {
        "client": client,
        "project_id": pid,
        "entity_id": eid,
        "evidence_dir": test_evidence_dir,
    }


# ═══════════════════════════════════════════════════════════════
# Evidence Upload
# ═══════════════════════════════════════════════════════════════

class TestEvidenceUpload:
    """CAP-UP: Evidence upload endpoint tests."""

    def test_upload_png(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        data = {
            "file": (io.BytesIO(b"\x89PNG fake image data"), "screenshot.png"),
            "entity_id": str(eid),
            "project_id": str(pid),
        }
        r = c.post("/api/evidence/upload",
                    data=data, content_type="multipart/form-data")
        assert r.status_code == 201
        result = r.get_json()
        assert result["success"] is True
        assert len(result["evidence_paths"]) == 1
        assert len(result["evidence_ids"]) == 1

    def test_upload_pdf(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        data = {
            "file": (io.BytesIO(b"%PDF-1.4 content"), "report.pdf"),
            "entity_id": str(eid),
            "project_id": str(pid),
        }
        r = c.post("/api/evidence/upload",
                    data=data, content_type="multipart/form-data")
        assert r.status_code == 201
        result = r.get_json()
        assert result["success"] is True

    def test_upload_with_metadata(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        data = {
            "file": (io.BytesIO(b"csv data"), "data.csv"),
            "entity_id": str(eid),
            "project_id": str(pid),
            "source_name": "Exported from dashboard",
            "metadata": json.dumps({"rows": 100, "columns": 5}),
        }
        r = c.post("/api/evidence/upload",
                    data=data, content_type="multipart/form-data")
        assert r.status_code == 201
        result = r.get_json()
        assert result["metadata"]["rows"] == 100

    def test_upload_no_file(self, capture_project):
        c = capture_project["client"]
        r = c.post("/api/evidence/upload",
                    data={"entity_id": "1", "project_id": "1"},
                    content_type="multipart/form-data")
        assert r.status_code == 400
        assert "No file" in r.get_json()["error"]

    def test_upload_no_entity_id(self, capture_project):
        c = capture_project["client"]
        data = {
            "file": (io.BytesIO(b"data"), "test.png"),
            "project_id": str(capture_project["project_id"]),
        }
        r = c.post("/api/evidence/upload",
                    data=data, content_type="multipart/form-data")
        assert r.status_code == 400
        assert "entity_id" in r.get_json()["error"]

    def test_upload_invalid_entity(self, capture_project):
        c = capture_project["client"]
        data = {
            "file": (io.BytesIO(b"data"), "test.png"),
            "entity_id": "99999",
            "project_id": str(capture_project["project_id"]),
        }
        r = c.post("/api/evidence/upload",
                    data=data, content_type="multipart/form-data")
        assert r.status_code == 404

    def test_upload_bad_extension(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        data = {
            "file": (io.BytesIO(b"malicious"), "virus.exe"),
            "entity_id": str(eid),
            "project_id": str(pid),
        }
        r = c.post("/api/evidence/upload",
                    data=data, content_type="multipart/form-data")
        assert r.status_code == 400
        assert "not allowed" in r.get_json()["error"].lower()

    def test_upload_creates_db_record(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        data = {
            "file": (io.BytesIO(b"\x89PNG data"), "screen.png"),
            "entity_id": str(eid),
            "project_id": str(pid),
        }
        r = c.post("/api/evidence/upload",
                    data=data, content_type="multipart/form-data")
        assert r.status_code == 201
        ev_id = r.get_json()["evidence_ids"][0]

        # Verify via existing evidence API
        r2 = c.get(f"/api/entities/{eid}/evidence")
        assert r2.status_code == 200
        evidence = r2.get_json()
        assert any(e["id"] == ev_id for e in evidence)


# ═══════════════════════════════════════════════════════════════
# Evidence File Serving
# ═══════════════════════════════════════════════════════════════

class TestEvidenceServe:
    """CAP-SRV: Evidence file serving endpoint tests."""

    def test_serve_uploaded_file(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        # Upload a file first
        file_content = b"\x89PNG test image data"
        data = {
            "file": (io.BytesIO(file_content), "test.png"),
            "entity_id": str(eid),
            "project_id": str(pid),
        }
        r = c.post("/api/evidence/upload",
                    data=data, content_type="multipart/form-data")
        ev_id = r.get_json()["evidence_ids"][0]

        # Serve the file
        r2 = c.get(f"/api/evidence/{ev_id}/file")
        assert r2.status_code == 200
        assert r2.data == file_content

    def test_serve_nonexistent_evidence(self, capture_project):
        c = capture_project["client"]
        r = c.get("/api/evidence/99999/file")
        assert r.status_code == 404

    def test_serve_missing_file_on_disk(self, capture_project):
        c = capture_project["client"]
        eid = capture_project["entity_id"]

        # Create evidence record pointing to nonexistent file
        ev_id = c.db.add_evidence(
            eid, "screenshot", "nonexistent/path.png",
        )
        r = c.get(f"/api/evidence/{ev_id}/file")
        assert r.status_code == 404
        assert "not found on disk" in r.get_json()["error"]


# ═══════════════════════════════════════════════════════════════
# Evidence File Deletion
# ═══════════════════════════════════════════════════════════════

class TestEvidenceDelete:
    """CAP-DEL: Evidence file + record deletion tests."""

    def test_delete_uploaded_file(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        # Upload
        data = {
            "file": (io.BytesIO(b"delete me"), "temp.txt"),
            "entity_id": str(eid),
            "project_id": str(pid),
        }
        r = c.post("/api/evidence/upload",
                    data=data, content_type="multipart/form-data")
        ev_id = r.get_json()["evidence_ids"][0]
        file_path = r.get_json()["evidence_paths"][0]

        # Delete
        r2 = c.delete(f"/api/evidence/{ev_id}/file")
        assert r2.status_code == 200
        result = r2.get_json()
        assert result["file_deleted"] is True
        assert result["record_deleted"] is True

        # Verify file gone from disk
        evidence_dir = capture_project["evidence_dir"]
        assert not (evidence_dir / file_path).exists()

        # Verify DB record gone
        ev = c.db.get_evidence_by_id(ev_id)
        assert ev is None

    def test_delete_nonexistent_evidence(self, capture_project):
        c = capture_project["client"]
        r = c.delete("/api/evidence/99999/file")
        assert r.status_code == 404

    def test_delete_record_with_missing_file(self, capture_project):
        c = capture_project["client"]
        eid = capture_project["entity_id"]

        # Create record pointing to nonexistent file
        ev_id = c.db.add_evidence(eid, "screenshot", "ghost/path.png")

        r = c.delete(f"/api/evidence/{ev_id}/file")
        assert r.status_code == 200
        assert r.get_json()["file_deleted"] is False
        assert r.get_json()["record_deleted"] is True


# ═══════════════════════════════════════════════════════════════
# Document Capture API
# ═══════════════════════════════════════════════════════════════

class TestDocumentCaptureAPI:
    """CAP-DOC: Document capture endpoint tests."""

    def test_capture_pdf(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/pdf"}
        mock_resp.content = b"%PDF-1.4 fake"
        mock_resp.raise_for_status = MagicMock()

        with patch("core.capture.requests.get", return_value=mock_resp):
            r = c.post("/api/capture/document", json={
                "url": "https://example.com/doc.pdf",
                "entity_id": eid,
                "project_id": pid,
            })
        assert r.status_code == 201
        result = r.get_json()
        assert result["success"] is True
        assert len(result["evidence_ids"]) == 1

    def test_capture_document_missing_url(self, capture_project):
        c = capture_project["client"]
        r = c.post("/api/capture/document", json={
            "entity_id": capture_project["entity_id"],
            "project_id": capture_project["project_id"],
        })
        assert r.status_code == 400
        assert "url" in r.get_json()["error"]

    def test_capture_document_missing_entity(self, capture_project):
        c = capture_project["client"]
        r = c.post("/api/capture/document", json={
            "url": "https://example.com/doc.pdf",
            "project_id": capture_project["project_id"],
        })
        assert r.status_code == 400
        assert "entity_id" in r.get_json()["error"]

    def test_capture_document_invalid_entity(self, capture_project):
        c = capture_project["client"]
        r = c.post("/api/capture/document", json={
            "url": "https://example.com/doc.pdf",
            "entity_id": 99999,
            "project_id": capture_project["project_id"],
        })
        assert r.status_code == 404

    def test_capture_document_download_failure(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        import requests as req_lib
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req_lib.HTTPError("404")

        with patch("core.capture.requests.get", return_value=mock_resp):
            r = c.post("/api/capture/document", json={
                "url": "https://example.com/missing.pdf",
                "entity_id": eid,
                "project_id": pid,
            })
        assert r.status_code == 422
        assert r.get_json()["success"] is False


# ═══════════════════════════════════════════════════════════════
# Website Capture API (mocked Playwright)
# ═══════════════════════════════════════════════════════════════

class TestWebsiteCaptureAPI:
    """CAP-WEB: Website capture endpoint tests (mocked Playwright)."""

    def test_capture_website_success(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        mock_result = CaptureResult(
            success=True,
            url="https://example.com",
            evidence_paths=[
                f"{pid}/{eid}/screenshot/example-com_20260220_abc.png",
                f"{pid}/{eid}/page_archive/example-com_20260220_abc.html",
            ],
            metadata={"title": "Example", "status_code": 200},
            duration_ms=1500,
        )

        with patch("web.blueprints.capture.capture_website", return_value=mock_result) as mock_cap:
            r = c.post("/api/capture/website", json={
                "url": "https://example.com",
                "entity_id": eid,
                "project_id": pid,
            })
            mock_cap.assert_called_once()

        assert r.status_code == 201
        result = r.get_json()
        assert result["success"] is True
        assert len(result["evidence_paths"]) == 2

    def test_capture_website_failure(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        mock_result = CaptureResult(
            success=False,
            url="https://bad.com",
            error="Connection refused",
        )

        with patch("web.blueprints.capture.capture_website", return_value=mock_result):
            r = c.post("/api/capture/website", json={
                "url": "https://bad.com",
                "entity_id": eid,
                "project_id": pid,
            })
        assert r.status_code == 422
        assert r.get_json()["success"] is False

    def test_capture_website_missing_url(self, capture_project):
        c = capture_project["client"]
        r = c.post("/api/capture/website", json={
            "entity_id": capture_project["entity_id"],
            "project_id": capture_project["project_id"],
        })
        assert r.status_code == 400

    def test_capture_website_invalid_entity(self, capture_project):
        c = capture_project["client"]
        r = c.post("/api/capture/website", json={
            "url": "https://example.com",
            "entity_id": 99999,
            "project_id": capture_project["project_id"],
        })
        assert r.status_code == 404

    def test_capture_website_with_options(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        mock_result = CaptureResult(success=True, url="https://example.com",
                                     evidence_paths=[], duration_ms=100)

        with patch("web.blueprints.capture.capture_website", return_value=mock_result) as mock_cap:
            r = c.post("/api/capture/website", json={
                "url": "https://example.com",
                "entity_id": eid,
                "project_id": pid,
                "full_page": False,
                "viewport_width": 1920,
                "save_html": False,
            })
            # Verify kwargs were passed
            call_kwargs = mock_cap.call_args
            assert call_kwargs.kwargs.get("full_page") is False or \
                   call_kwargs[1].get("full_page") is False

        assert r.status_code == 201

    def test_capture_website_auto_https(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        mock_result = CaptureResult(success=True, url="https://example.com",
                                     evidence_paths=[], duration_ms=100)

        with patch("web.blueprints.capture.capture_website", return_value=mock_result) as mock_cap:
            r = c.post("/api/capture/website", json={
                "url": "example.com",  # No scheme
                "entity_id": eid,
                "project_id": pid,
            })
            # Should have prepended https://
            call_args = mock_cap.call_args
            assert call_args.kwargs.get("url", call_args[1].get("url", "")).startswith("https://") or \
                   "https://example.com" in str(call_args)

        assert r.status_code == 201


# ═══════════════════════════════════════════════════════════════
# Evidence Stats
# ═══════════════════════════════════════════════════════════════

class TestEvidenceStats:
    """CAP-STAT: Evidence storage stats endpoint tests."""

    def test_stats_empty_project(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]

        r = c.get(f"/api/evidence/stats?project_id={pid}")
        assert r.status_code == 200
        stats = r.get_json()
        assert stats["total_count"] == 0
        assert stats["total_size"] == 0

    def test_stats_with_evidence(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        # Upload two files
        for fname, content in [("img.png", b"\x89PNG" + b"x" * 100),
                                ("doc.pdf", b"%PDF" + b"y" * 200)]:
            data = {
                "file": (io.BytesIO(content), fname),
                "entity_id": str(eid),
                "project_id": str(pid),
            }
            c.post("/api/evidence/upload",
                   data=data, content_type="multipart/form-data")

        r = c.get(f"/api/evidence/stats?project_id={pid}")
        assert r.status_code == 200
        stats = r.get_json()
        assert stats["total_count"] == 2
        assert stats["total_size"] > 0
        assert "screenshot" in stats["by_type"]
        assert "document" in stats["by_type"]

    def test_stats_missing_project_id(self, capture_project):
        c = capture_project["client"]
        r = c.get("/api/evidence/stats")
        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════
# Capture Jobs
# ═══════════════════════════════════════════════════════════════

class TestCaptureJobs:
    """CAP-JOB: Background capture job endpoint tests."""

    def test_list_jobs_empty(self, capture_project):
        c = capture_project["client"]
        r = c.get("/api/capture/jobs")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_get_nonexistent_job(self, capture_project):
        c = capture_project["client"]
        r = c.get("/api/capture/jobs/nonexistent_id")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Integration: Upload → Serve → Delete cycle
# ═══════════════════════════════════════════════════════════════

class TestUploadServDeleteCycle:
    """CAP-INT: Full upload → serve → delete integration test."""

    def test_full_cycle(self, capture_project):
        c = capture_project["client"]
        pid = capture_project["project_id"]
        eid = capture_project["entity_id"]

        file_content = b"Important research document content"

        # 1. Upload
        data = {
            "file": (io.BytesIO(file_content), "research.txt"),
            "entity_id": str(eid),
            "project_id": str(pid),
            "source_name": "Field notes",
        }
        r1 = c.post("/api/evidence/upload",
                     data=data, content_type="multipart/form-data")
        assert r1.status_code == 201
        ev_id = r1.get_json()["evidence_ids"][0]

        # 2. Verify in entity evidence list
        r2 = c.get(f"/api/entities/{eid}/evidence")
        assert r2.status_code == 200
        assert any(e["id"] == ev_id for e in r2.get_json())

        # 3. Serve the file
        r3 = c.get(f"/api/evidence/{ev_id}/file")
        assert r3.status_code == 200
        assert r3.data == file_content

        # 4. Check stats
        r4 = c.get(f"/api/evidence/stats?project_id={pid}")
        assert r4.status_code == 200
        assert r4.get_json()["total_count"] == 1

        # 5. Delete file + record
        r5 = c.delete(f"/api/evidence/{ev_id}/file")
        assert r5.status_code == 200
        assert r5.get_json()["file_deleted"] is True

        # 6. Verify gone
        r6 = c.get(f"/api/evidence/{ev_id}/file")
        assert r6.status_code == 404

        r7 = c.get(f"/api/evidence/stats?project_id={pid}")
        assert r7.get_json()["total_count"] == 0

"""Tests for the Capture Engine — file storage, evidence operations, upload validation.

Covers:
- File storage utilities (path generation, slugify, store/delete/exists)
- Evidence type guessing
- Upload validation
- Document download (mocked HTTP)
- Manual upload flow
- Evidence get_by_id DB method
- Capture result dataclass

Run: pytest tests/test_capture.py -v
Markers: db, capture
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.capture import (
    _slugify,
    _url_to_filename,
    _generate_filename,
    evidence_dir_for,
    evidence_path_relative,
    evidence_path_absolute,
    store_file,
    delete_file,
    file_exists,
    file_size,
    validate_upload,
    guess_evidence_type,
    get_mime_type,
    store_upload,
    capture_document,
    CaptureResult,
    EVIDENCE_DIR,
    ALLOWED_EVIDENCE_TYPES,
    ALLOWED_UPLOAD_EXTENSIONS,
    MAX_UPLOAD_SIZE,
    _content_type_to_ext,
    _type_from_path,
)

pytestmark = [pytest.mark.db, pytest.mark.capture]


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def evidence_tmpdir(tmp_path, monkeypatch):
    """Redirect EVIDENCE_DIR to a temp directory for test isolation."""
    import core.capture as capture_mod
    test_evidence_dir = tmp_path / "evidence"
    test_evidence_dir.mkdir()
    monkeypatch.setattr(capture_mod, "EVIDENCE_DIR", test_evidence_dir)
    return test_evidence_dir


@pytest.fixture
def entity_project(tmp_path):
    """Create a DB with a project and entity for evidence tests."""
    from storage.db import Database
    db = Database(db_path=tmp_path / "test.db")
    pid = db.create_project(
        name="Capture Test Project",
        purpose="Testing capture engine",
        entity_schema={
            "version": 1,
            "entity_types": [
                {"name": "Company", "slug": "company", "attributes": []}
            ],
            "relationships": [],
        },
    )
    eid = db.create_entity(pid, "company", "Test Corp")
    return {"db": db, "project_id": pid, "entity_id": eid}


# ═══════════════════════════════════════════════════════════════
# Slug and Filename Utilities
# ═══════════════════════════════════════════════════════════════

class TestSlugify:
    """Tests for _slugify helper."""

    def test_basic_slugify(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars_removed(self):
        result = _slugify("foo@bar.com/path?q=1")
        # Special chars (@, ., /, ?, =) are stripped; letters kept
        assert "@" not in result
        assert "?" not in result

    def test_empty_returns_unnamed(self):
        assert _slugify("") == "unnamed"

    def test_truncates_long_strings(self):
        result = _slugify("a" * 200)
        assert len(result) <= 80


class TestUrlToFilename:
    """Tests for _url_to_filename helper."""

    def test_basic_url(self):
        result = _url_to_filename("https://example.com")
        assert "example" in result

    def test_url_with_path(self):
        result = _url_to_filename("https://example.com/pricing/plans")
        assert "example" in result
        assert "pricing" in result

    def test_www_stripped(self):
        result = _url_to_filename("https://www.example.com")
        assert "www" not in result

    def test_truncates_long_urls(self):
        result = _url_to_filename(f"https://example.com/{'a' * 200}")
        assert len(result) <= 100


class TestGenerateFilename:
    """Tests for _generate_filename helper."""

    def test_generates_with_extension(self):
        result = _generate_filename("test-site", ".png")
        assert result.endswith(".png")
        assert "test-site" in result

    def test_includes_timestamp(self):
        result = _generate_filename("prefix", ".html")
        # Should contain date digits
        assert any(c.isdigit() for c in result)

    def test_unique_filenames(self):
        a = _generate_filename("same", ".png")
        b = _generate_filename("same", ".png")
        assert a != b  # hash suffix differs


# ═══════════════════════════════════════════════════════════════
# File Storage
# ═══════════════════════════════════════════════════════════════

class TestFileStorage:
    """Tests for file storage operations."""

    def test_evidence_dir_for_creates_directory(self, evidence_tmpdir):
        d = evidence_dir_for(1, 10, "screenshot")
        assert d.exists()
        assert d.is_dir()
        assert str(d).endswith("1/10/screenshot")

    def test_evidence_dir_for_invalid_type(self, evidence_tmpdir):
        with pytest.raises(ValueError, match="Invalid evidence type"):
            evidence_dir_for(1, 10, "invalid_type")

    def test_evidence_path_relative(self):
        result = evidence_path_relative(1, 10, "screenshot", "test.png")
        assert result == "1/10/screenshot/test.png"

    def test_evidence_path_absolute(self):
        result = evidence_path_absolute("1/10/screenshot/test.png")
        assert str(result).endswith("1/10/screenshot/test.png")
        assert EVIDENCE_DIR in result.parents or result.parent.parent.parent.parent == EVIDENCE_DIR

    def test_store_file(self, evidence_tmpdir):
        data = b"PNG file data here"
        rel_path = store_file(1, 10, "screenshot", data, "test.png")
        assert rel_path == "1/10/screenshot/test.png"
        abs_path = evidence_tmpdir / rel_path
        assert abs_path.exists()
        assert abs_path.read_bytes() == data

    def test_file_exists(self, evidence_tmpdir):
        store_file(1, 10, "screenshot", b"data", "exists.png")
        assert file_exists("1/10/screenshot/exists.png")
        assert not file_exists("1/10/screenshot/missing.png")

    def test_file_size(self, evidence_tmpdir):
        data = b"x" * 1024
        store_file(1, 10, "document", data, "doc.pdf")
        assert file_size("1/10/document/doc.pdf") == 1024
        assert file_size("nonexistent/path.pdf") == 0

    def test_delete_file(self, evidence_tmpdir):
        store_file(1, 10, "screenshot", b"data", "delete_me.png")
        assert file_exists("1/10/screenshot/delete_me.png")
        result = delete_file("1/10/screenshot/delete_me.png")
        assert result is True
        assert not file_exists("1/10/screenshot/delete_me.png")

    def test_delete_nonexistent_file(self, evidence_tmpdir):
        result = delete_file("1/10/screenshot/ghost.png")
        assert result is False

    def test_delete_cleans_empty_dirs(self, evidence_tmpdir):
        store_file(99, 88, "screenshot", b"data", "only.png")
        delete_file("99/88/screenshot/only.png")
        # Empty parent dirs should be cleaned up
        assert not (evidence_tmpdir / "99" / "88" / "screenshot").exists()


# ═══════════════════════════════════════════════════════════════
# Upload Validation
# ═══════════════════════════════════════════════════════════════

class TestUploadValidation:
    """Tests for validate_upload."""

    def test_valid_png(self):
        valid, err = validate_upload("screenshot.png", 1024)
        assert valid
        assert err == ""

    def test_valid_pdf(self):
        valid, err = validate_upload("document.pdf", 5000)
        assert valid

    def test_no_filename(self):
        valid, err = validate_upload("", 1024)
        assert not valid
        assert "filename" in err.lower()

    def test_disallowed_extension(self):
        valid, err = validate_upload("malware.exe", 1024)
        assert not valid
        assert "not allowed" in err.lower()

    def test_too_large(self):
        valid, err = validate_upload("big.png", MAX_UPLOAD_SIZE + 1)
        assert not valid
        assert "too large" in err.lower()

    def test_empty_file(self):
        valid, err = validate_upload("empty.png", 0)
        assert not valid
        assert "empty" in err.lower()


# ═══════════════════════════════════════════════════════════════
# Evidence Type Guessing
# ═══════════════════════════════════════════════════════════════

class TestGuessEvidenceType:
    """Tests for guess_evidence_type."""

    def test_png_is_screenshot(self):
        assert guess_evidence_type("capture.png") == "screenshot"

    def test_jpg_is_screenshot(self):
        assert guess_evidence_type("photo.jpg") == "screenshot"

    def test_pdf_is_document(self):
        assert guess_evidence_type("report.pdf") == "document"

    def test_html_is_page_archive(self):
        assert guess_evidence_type("page.html") == "page_archive"

    def test_mp4_is_video(self):
        assert guess_evidence_type("demo.mp4") == "video"

    def test_unknown_is_other(self):
        assert guess_evidence_type("file.xyz") == "other"

    def test_csv_is_document(self):
        assert guess_evidence_type("data.csv") == "document"


class TestGetMimeType:
    """Tests for get_mime_type."""

    def test_png_mime(self):
        assert get_mime_type("1/2/screenshot/img.png") == "image/png"

    def test_pdf_mime(self):
        assert get_mime_type("1/2/document/doc.pdf") == "application/pdf"

    def test_html_mime(self):
        assert get_mime_type("1/2/page_archive/page.html") == "text/html"

    def test_unknown_mime(self):
        assert get_mime_type("1/2/other/file.zzz123") == "application/octet-stream"


# ═══════════════════════════════════════════════════════════════
# Content Type to Extension
# ═══════════════════════════════════════════════════════════════

class TestContentTypeToExt:
    """Tests for _content_type_to_ext."""

    def test_pdf_content_type(self):
        assert _content_type_to_ext("application/pdf", "https://x.com/doc") == ".pdf"

    def test_html_content_type(self):
        assert _content_type_to_ext("text/html; charset=utf-8", "https://x.com") == ".html"

    def test_fallback_to_url_extension(self):
        assert _content_type_to_ext("application/octet-stream", "https://x.com/file.xlsx") == ".xlsx"

    def test_unknown_returns_bin(self):
        assert _content_type_to_ext("application/mystery", "https://x.com/noext") == ".bin"


# ═══════════════════════════════════════════════════════════════
# Type from Path
# ═══════════════════════════════════════════════════════════════

class TestTypeFromPath:
    """Tests for _type_from_path."""

    def test_screenshot_path(self):
        assert _type_from_path("1/10/screenshot/img.png") == "screenshot"

    def test_document_path(self):
        assert _type_from_path("1/10/document/doc.pdf") == "document"

    def test_fallback_on_short_path(self):
        # Should fall back to guessing from extension
        assert _type_from_path("img.png") == "screenshot"


# ═══════════════════════════════════════════════════════════════
# CaptureResult Dataclass
# ═══════════════════════════════════════════════════════════════

class TestCaptureResult:
    """Tests for CaptureResult."""

    def test_success_result(self):
        r = CaptureResult(success=True, url="https://example.com",
                          evidence_paths=["1/2/screenshot/img.png"],
                          evidence_ids=[42], duration_ms=500)
        d = r.to_dict()
        assert d["success"] is True
        assert d["url"] == "https://example.com"
        assert 42 in d["evidence_ids"]

    def test_failure_result(self):
        r = CaptureResult(success=False, url="https://bad.com",
                          error="Connection refused")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "Connection refused"

    def test_defaults(self):
        r = CaptureResult(success=True, url="https://x.com")
        assert r.evidence_paths == []
        assert r.evidence_ids == []
        assert r.metadata == {}
        assert r.duration_ms == 0


# ═══════════════════════════════════════════════════════════════
# Manual Upload (store_upload)
# ═══════════════════════════════════════════════════════════════

class TestStoreUpload:
    """Tests for the store_upload function."""

    def test_store_png_upload(self, evidence_tmpdir):
        result = store_upload(
            project_id=1, entity_id=10,
            file_data=b"\x89PNG fake image data",
            original_filename="screenshot.png",
        )
        assert result.success
        assert len(result.evidence_paths) == 1
        abs_path = evidence_tmpdir / result.evidence_paths[0]
        assert abs_path.exists()

    def test_store_pdf_upload(self, evidence_tmpdir):
        result = store_upload(
            project_id=1, entity_id=10,
            file_data=b"%PDF-1.4 fake pdf content",
            original_filename="report.pdf",
        )
        assert result.success
        assert "document" in result.evidence_paths[0]

    def test_upload_invalid_extension(self, evidence_tmpdir):
        result = store_upload(
            project_id=1, entity_id=10,
            file_data=b"malware",
            original_filename="virus.exe",
        )
        assert not result.success
        assert "not allowed" in result.error.lower()

    def test_upload_empty_file(self, evidence_tmpdir):
        result = store_upload(
            project_id=1, entity_id=10,
            file_data=b"",
            original_filename="empty.png",
        )
        assert not result.success
        assert "empty" in result.error.lower()

    def test_upload_with_db(self, evidence_tmpdir, entity_project):
        db = entity_project["db"]
        pid = entity_project["project_id"]
        eid = entity_project["entity_id"]

        result = store_upload(
            project_id=pid, entity_id=eid,
            file_data=b"\x89PNG test data",
            original_filename="test.png",
            db=db,
            source_name="Test upload",
        )
        assert result.success
        assert len(result.evidence_ids) == 1

        # Verify DB record
        ev = db.get_evidence_by_id(result.evidence_ids[0])
        assert ev is not None
        assert ev["evidence_type"] == "screenshot"
        assert ev["source_name"] == "Test upload"
        assert ev["metadata"]["original_filename"] == "test.png"

    def test_upload_with_metadata(self, evidence_tmpdir):
        result = store_upload(
            project_id=1, entity_id=10,
            file_data=b"data",
            original_filename="doc.pdf",
            metadata={"author": "Test User", "pages": 5},
        )
        assert result.success
        assert result.metadata["author"] == "Test User"
        assert result.metadata["pages"] == 5

    def test_upload_override_evidence_type(self, evidence_tmpdir):
        result = store_upload(
            project_id=1, entity_id=10,
            file_data=b"data",
            original_filename="image.png",
            evidence_type="other",  # Override: not screenshot
        )
        assert result.success
        assert "other" in result.evidence_paths[0]


# ═══════════════════════════════════════════════════════════════
# Document Capture (mocked HTTP)
# ═══════════════════════════════════════════════════════════════

class TestCaptureDocument:
    """Tests for capture_document with mocked HTTP requests."""

    def test_capture_pdf(self, evidence_tmpdir):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/pdf"}
        mock_resp.content = b"%PDF-1.4 fake content"
        mock_resp.raise_for_status = MagicMock()

        with patch("core.capture.requests.get", return_value=mock_resp):
            result = capture_document(
                url="https://example.com/doc.pdf",
                project_id=1, entity_id=10,
            )
        assert result.success
        assert len(result.evidence_paths) == 1
        assert result.metadata["content_type"] == "application/pdf"

    def test_capture_html_page(self, evidence_tmpdir):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.content = b"<html><body>Hello</body></html>"
        mock_resp.raise_for_status = MagicMock()

        with patch("core.capture.requests.get", return_value=mock_resp):
            result = capture_document(
                url="https://example.com/help",
                project_id=1, entity_id=10,
            )
        assert result.success
        assert "page_archive" in result.evidence_paths[0]

    def test_capture_document_with_db(self, evidence_tmpdir, entity_project):
        db = entity_project["db"]
        pid = entity_project["project_id"]
        eid = entity_project["entity_id"]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/pdf"}
        mock_resp.content = b"%PDF-1.4 test"
        mock_resp.raise_for_status = MagicMock()

        with patch("core.capture.requests.get", return_value=mock_resp):
            result = capture_document(
                url="https://example.com/report.pdf",
                project_id=pid, entity_id=eid, db=db,
            )
        assert result.success
        assert len(result.evidence_ids) == 1

        ev = db.get_evidence_by_id(result.evidence_ids[0])
        assert ev is not None
        assert ev["source_url"] == "https://example.com/report.pdf"

    def test_capture_document_http_error(self, evidence_tmpdir):
        import requests as req_lib
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req_lib.HTTPError("404 Not Found")

        with patch("core.capture.requests.get", return_value=mock_resp):
            result = capture_document(
                url="https://example.com/missing.pdf",
                project_id=1, entity_id=10,
            )
        assert not result.success
        assert "Download failed" in result.error

    def test_capture_document_timeout(self, evidence_tmpdir):
        import requests as req_lib
        with patch("core.capture.requests.get", side_effect=req_lib.Timeout("timed out")):
            result = capture_document(
                url="https://slow.com/big.pdf",
                project_id=1, entity_id=10,
                timeout=1,
            )
        assert not result.success
        assert "Download failed" in result.error

    def test_capture_document_too_large(self, evidence_tmpdir):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/pdf"}
        mock_resp.content = b"x" * (MAX_UPLOAD_SIZE + 1)
        mock_resp.raise_for_status = MagicMock()

        with patch("core.capture.requests.get", return_value=mock_resp):
            result = capture_document(
                url="https://example.com/huge.pdf",
                project_id=1, entity_id=10,
            )
        assert not result.success
        assert "too large" in result.error.lower()


# ═══════════════════════════════════════════════════════════════
# DB: get_evidence_by_id
# ═══════════════════════════════════════════════════════════════

class TestGetEvidenceById:
    """Tests for the new get_evidence_by_id DB method."""

    def test_get_existing(self, entity_project):
        db = entity_project["db"]
        eid = entity_project["entity_id"]

        ev_id = db.add_evidence(
            eid, "screenshot", "test/path.png",
            source_url="https://example.com",
            source_name="Test",
            metadata={"width": 800},
        )

        ev = db.get_evidence_by_id(ev_id)
        assert ev is not None
        assert ev["id"] == ev_id
        assert ev["evidence_type"] == "screenshot"
        assert ev["file_path"] == "test/path.png"
        assert ev["source_url"] == "https://example.com"
        assert ev["metadata"]["width"] == 800

    def test_get_nonexistent(self, entity_project):
        db = entity_project["db"]
        ev = db.get_evidence_by_id(99999)
        assert ev is None

    def test_get_after_delete(self, entity_project):
        db = entity_project["db"]
        eid = entity_project["entity_id"]

        ev_id = db.add_evidence(eid, "document", "test/doc.pdf")
        db.delete_evidence(ev_id)
        ev = db.get_evidence_by_id(ev_id)
        assert ev is None

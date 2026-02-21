"""Capture engine — file storage, headless website capture, document download.

Phase 2 of the Research Workbench: evidence collection from web sources.

File storage layout:
    {DATA_DIR}/evidence/{project_id}/{entity_id}/{evidence_type}/{filename}

Supports:
    - Full-page screenshots (PNG) via Playwright
    - HTML page archival (full page source)
    - PDF/HTML document download
    - Manual file upload (any type)
    - Thumbnail generation for screenshots
"""
import asyncio
import hashlib
import mimetypes
import re
import threading
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from loguru import logger

from config import DATA_DIR


# ── File Storage ──────────────────────────────────────────────

EVIDENCE_DIR = DATA_DIR / "evidence"
MAX_FILENAME_LENGTH = 200
ALLOWED_EVIDENCE_TYPES = {"screenshot", "document", "page_archive", "video", "other"}
ALLOWED_UPLOAD_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",  # images
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",          # documents
    ".html", ".htm", ".mhtml",                          # web archives
    ".mp4", ".mov", ".webm",                            # video
    ".json", ".csv", ".txt", ".md",                     # data/text
}
# Max file size for uploads (50 MB)
MAX_UPLOAD_SIZE = 50 * 1024 * 1024


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:80] or "unnamed"


def _url_to_filename(url: str) -> str:
    """Convert a URL to a safe filename component."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").replace(":", "-")
    path = parsed.path.strip("/").replace("/", "_")
    slug = _slugify(f"{domain}_{path}" if path else domain)
    return slug[:100]


def _generate_filename(prefix: str, extension: str) -> str:
    """Generate a unique filename with timestamp + short hash."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Short random suffix to prevent collisions
    suffix = hashlib.md5(f"{time.time()}{threading.get_ident()}".encode()).hexdigest()[:8]
    name = f"{prefix}_{ts}_{suffix}{extension}"
    if len(name) > MAX_FILENAME_LENGTH:
        name = name[:MAX_FILENAME_LENGTH - len(extension)] + extension
    return name


def evidence_dir_for(project_id: int, entity_id: int, evidence_type: str) -> Path:
    """Get the evidence directory for a specific entity and type. Creates it if needed."""
    if evidence_type not in ALLOWED_EVIDENCE_TYPES:
        raise ValueError(f"Invalid evidence type: {evidence_type}")
    d = EVIDENCE_DIR / str(project_id) / str(entity_id) / evidence_type
    d.mkdir(parents=True, exist_ok=True)
    return d


def evidence_path_relative(project_id: int, entity_id: int,
                           evidence_type: str, filename: str) -> str:
    """Get the relative path for evidence storage (stored in DB)."""
    return f"{project_id}/{entity_id}/{evidence_type}/{filename}"


def evidence_path_absolute(relative_path: str) -> Path:
    """Convert a relative evidence path to an absolute filesystem path.

    Raises ValueError if the resolved path escapes EVIDENCE_DIR (path traversal).
    """
    base = EVIDENCE_DIR.resolve()
    target = (EVIDENCE_DIR / relative_path).resolve()
    if not target.is_relative_to(base):
        raise ValueError("Path traversal detected")
    return target


def store_file(project_id: int, entity_id: int, evidence_type: str,
               data: bytes, filename: str) -> str:
    """Write file data to the evidence directory.

    Args:
        project_id: Project ID
        entity_id: Entity ID
        evidence_type: One of ALLOWED_EVIDENCE_TYPES
        data: Raw file bytes
        filename: Desired filename (will be placed in correct directory)

    Returns:
        Relative path string for DB storage
    """
    d = evidence_dir_for(project_id, entity_id, evidence_type)
    filepath = d / filename
    filepath.write_bytes(data)
    return evidence_path_relative(project_id, entity_id, evidence_type, filename)


def delete_file(relative_path: str) -> bool:
    """Delete an evidence file from disk.

    Returns True if file was deleted, False if it didn't exist.
    """
    abs_path = evidence_path_absolute(relative_path)
    if abs_path.exists():
        abs_path.unlink()
        # Clean up empty parent directories
        for parent in [abs_path.parent, abs_path.parent.parent, abs_path.parent.parent.parent]:
            if parent != EVIDENCE_DIR and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        return True
    return False


def file_exists(relative_path: str) -> bool:
    """Check if an evidence file exists on disk."""
    return evidence_path_absolute(relative_path).exists()


def file_size(relative_path: str) -> int:
    """Get the size of an evidence file in bytes. Returns 0 if not found."""
    abs_path = evidence_path_absolute(relative_path)
    return abs_path.stat().st_size if abs_path.exists() else 0


def validate_upload(filename: str, size: int) -> tuple[bool, str]:
    """Validate an uploaded file.

    Returns (is_valid, error_message).
    """
    if not filename:
        return False, "No filename provided"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        return False, f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
    if size > MAX_UPLOAD_SIZE:
        return False, f"File too large ({size / 1024 / 1024:.1f} MB). Maximum: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f} MB"
    if size == 0:
        return False, "Empty file"
    return True, ""


def guess_evidence_type(filename: str) -> str:
    """Guess the evidence type from a filename's extension."""
    ext = Path(filename).suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        return "screenshot"
    if ext in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".md", ".json"}:
        return "document"
    if ext in {".html", ".htm", ".mhtml"}:
        return "page_archive"
    if ext in {".mp4", ".mov", ".webm"}:
        return "video"
    return "other"


def get_mime_type(relative_path: str) -> str:
    """Get MIME type for an evidence file."""
    mime, _ = mimetypes.guess_type(relative_path)
    return mime or "application/octet-stream"


# ── Capture Results ───────────────────────────────────────────

@dataclass
class CaptureResult:
    """Result of a capture operation."""
    success: bool
    url: str
    evidence_paths: list[str] = field(default_factory=list)  # relative paths
    evidence_ids: list[int] = field(default_factory=list)     # DB evidence IDs
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    duration_ms: int = 0

    def to_dict(self):
        return asdict(self)


# ── Headless Website Capture ──────────────────────────────────

# Reuse browser pool from core/scraper.py
from core.scraper import _get_browser, _get_or_create_loop, _USER_AGENT


async def _capture_website_async(
    url: str,
    project_id: int,
    entity_id: int,
    full_page: bool = True,
    viewport_width: int = 1440,
    viewport_height: int = 900,
    wait_ms: int = 3000,
    timeout_ms: int = 30000,
    save_html: bool = True,
) -> CaptureResult:
    """Capture a website: full-page screenshot + optional HTML archive.

    Args:
        url: URL to capture
        project_id: Project to store evidence under
        entity_id: Entity to link evidence to
        full_page: Capture entire scrollable page (True) or viewport only (False)
        viewport_width: Browser viewport width
        viewport_height: Browser viewport height
        wait_ms: Time to wait for JS rendering after load
        timeout_ms: Navigation timeout
        save_html: Also save the page HTML source

    Returns:
        CaptureResult with paths to stored files
    """
    start = time.time()
    evidence_paths = []

    try:
        _pw, browser = await _get_browser()
    except Exception as e:
        return CaptureResult(
            success=False, url=url,
            error=f"Browser launch failed: {e}",
            duration_ms=int((time.time() - start) * 1000),
        )

    context = await browser.new_context(
        user_agent=_USER_AGENT,
        viewport={"width": viewport_width, "height": viewport_height},
    )
    context.set_default_timeout(timeout_ms)
    page = await context.new_page()

    metadata = {
        "viewport_width": viewport_width,
        "viewport_height": viewport_height,
        "full_page": full_page,
    }

    try:
        response = await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        status_code = response.status if response else 0
        final_url = page.url
        metadata["status_code"] = status_code
        metadata["final_url"] = final_url

        if status_code >= 400:
            return CaptureResult(
                success=False, url=url,
                error=f"HTTP {status_code}",
                metadata=metadata,
                duration_ms=int((time.time() - start) * 1000),
            )

        # Wait for JS rendering
        await page.wait_for_timeout(wait_ms)

        # Get page title for filename
        title = await page.title() or ""
        metadata["title"] = title

        url_slug = _url_to_filename(url)

        # 1. Screenshot
        screenshot_name = _generate_filename(url_slug, ".png")
        screenshot_bytes = await page.screenshot(full_page=full_page)
        metadata["screenshot_size"] = len(screenshot_bytes)

        # Get actual page dimensions
        dimensions = await page.evaluate("""() => ({
            width: document.documentElement.scrollWidth,
            height: document.documentElement.scrollHeight,
        })""")
        metadata["page_width"] = dimensions.get("width", 0)
        metadata["page_height"] = dimensions.get("height", 0)

        screenshot_path = store_file(
            project_id, entity_id, "screenshot",
            screenshot_bytes, screenshot_name,
        )
        evidence_paths.append(("screenshot", screenshot_path, {
            **metadata,
            "width": dimensions.get("width", viewport_width),
            "height": dimensions.get("height", viewport_height),
            "format": "png",
        }))

        # 2. HTML archive (optional)
        if save_html:
            html_content = await page.content()
            html_name = _generate_filename(url_slug, ".html")
            html_bytes = html_content.encode("utf-8")
            metadata["html_size"] = len(html_bytes)

            html_path = store_file(
                project_id, entity_id, "page_archive",
                html_bytes, html_name,
            )
            evidence_paths.append(("page_archive", html_path, {
                "format": "html",
                "size": len(html_bytes),
                "title": title,
            }))

        return CaptureResult(
            success=True, url=url,
            evidence_paths=[p[1] for p in evidence_paths],
            metadata=metadata,
            duration_ms=int((time.time() - start) * 1000),
        )

    except Exception as e:
        return CaptureResult(
            success=False, url=url,
            error=str(e),
            metadata=metadata,
            duration_ms=int((time.time() - start) * 1000),
        )
    finally:
        await context.close()


def capture_website(
    url: str,
    project_id: int,
    entity_id: int,
    db=None,
    **kwargs,
) -> CaptureResult:
    """Synchronous wrapper for website capture.

    If db is provided, automatically creates evidence records.

    Args:
        url: URL to capture
        project_id: Project ID
        entity_id: Entity ID
        db: Database instance (optional — if provided, creates evidence records)
        **kwargs: Passed to _capture_website_async (full_page, viewport_width, etc.)

    Returns:
        CaptureResult with evidence_ids populated if db was provided
    """
    loop = _get_or_create_loop()
    deadline_s = (kwargs.get("timeout_ms", 30000) * 2) / 1000

    try:
        result = loop.run_until_complete(
            asyncio.wait_for(
                _capture_website_async(url, project_id, entity_id, **kwargs),
                timeout=deadline_s,
            )
        )
    except asyncio.TimeoutError:
        return CaptureResult(
            success=False, url=url,
            error=f"Capture deadline exceeded ({deadline_s:.0f}s)",
        )

    # Create evidence records in DB if db provided and capture succeeded
    if db and result.success:
        # Re-run the async function stored the files; now link them in DB
        # The evidence_paths list contains tuples from the async function,
        # but CaptureResult.evidence_paths only has the path strings.
        # We need to create evidence records for each file.
        for ev_path in result.evidence_paths:
            ev_type = _type_from_path(ev_path)
            ev_id = db.add_evidence(
                entity_id=entity_id,
                evidence_type=ev_type,
                file_path=ev_path,
                source_url=url,
                source_name="Website capture",
                metadata=result.metadata,
            )
            result.evidence_ids.append(ev_id)

    return result


def _type_from_path(relative_path: str) -> str:
    """Extract evidence type from a relative evidence path."""
    # Path format: {project_id}/{entity_id}/{evidence_type}/{filename}
    parts = relative_path.split("/")
    if len(parts) >= 3:
        return parts[2]
    return guess_evidence_type(relative_path)


# ── Document Capture ──────────────────────────────────────────

def capture_document(
    url: str,
    project_id: int,
    entity_id: int,
    db=None,
    timeout: int = 30,
) -> CaptureResult:
    """Download a document (PDF, HTML, etc.) from a URL and store as evidence.

    Args:
        url: URL to download
        project_id: Project ID
        entity_id: Entity ID
        db: Database instance (optional — if provided, creates evidence record)
        timeout: Request timeout in seconds

    Returns:
        CaptureResult
    """
    start = time.time()
    metadata = {"source_url": url}

    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
            allow_redirects=True,
            stream=True,
        )
        resp.raise_for_status()
    except Exception as e:
        return CaptureResult(
            success=False, url=url,
            error=f"Download failed: {e}",
            duration_ms=int((time.time() - start) * 1000),
        )

    # Determine file type from content-type header or URL
    content_type = resp.headers.get("Content-Type", "")
    metadata["content_type"] = content_type
    metadata["status_code"] = resp.status_code

    ext = _content_type_to_ext(content_type, url)
    evidence_type = guess_evidence_type(f"file{ext}")

    # Read content (with size limit)
    content = resp.content
    if len(content) > MAX_UPLOAD_SIZE:
        return CaptureResult(
            success=False, url=url,
            error=f"Document too large ({len(content) / 1024 / 1024:.1f} MB)",
            duration_ms=int((time.time() - start) * 1000),
        )

    metadata["file_size"] = len(content)
    url_slug = _url_to_filename(url)
    filename = _generate_filename(url_slug, ext)

    relative_path = store_file(project_id, entity_id, evidence_type, content, filename)

    result = CaptureResult(
        success=True, url=url,
        evidence_paths=[relative_path],
        metadata=metadata,
        duration_ms=int((time.time() - start) * 1000),
    )

    if db:
        ev_id = db.add_evidence(
            entity_id=entity_id,
            evidence_type=evidence_type,
            file_path=relative_path,
            source_url=url,
            source_name="Document capture",
            metadata=metadata,
        )
        result.evidence_ids.append(ev_id)

    return result


def _content_type_to_ext(content_type: str, url: str) -> str:
    """Determine file extension from content-type or URL."""
    ct = content_type.split(";")[0].strip().lower()
    ct_map = {
        "application/pdf": ".pdf",
        "text/html": ".html",
        "text/plain": ".txt",
        "application/json": ".json",
        "text/csv": ".csv",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    if ct in ct_map:
        return ct_map[ct]

    # Fall back to URL extension
    parsed = urlparse(url)
    path_ext = Path(parsed.path).suffix.lower()
    if path_ext in ALLOWED_UPLOAD_EXTENSIONS:
        return path_ext
    return ".bin"


# ── Manual Upload ─────────────────────────────────────────────

def store_upload(
    project_id: int,
    entity_id: int,
    file_data: bytes,
    original_filename: str,
    evidence_type: str = None,
    db=None,
    source_name: str = "Manual upload",
    metadata: dict = None,
) -> CaptureResult:
    """Store a manually uploaded file as evidence.

    Args:
        project_id: Project ID
        entity_id: Entity ID
        file_data: Raw file bytes
        original_filename: Original filename from upload
        evidence_type: Override evidence type (default: guessed from extension)
        db: Database instance (optional)
        source_name: Source description
        metadata: Additional metadata

    Returns:
        CaptureResult
    """
    start = time.time()

    # Validate
    is_valid, err = validate_upload(original_filename, len(file_data))
    if not is_valid:
        return CaptureResult(
            success=False, url="",
            error=err,
            duration_ms=int((time.time() - start) * 1000),
        )

    if not evidence_type:
        evidence_type = guess_evidence_type(original_filename)

    ext = Path(original_filename).suffix.lower()
    safe_name = _slugify(Path(original_filename).stem)
    filename = _generate_filename(safe_name, ext)

    meta = {
        "original_filename": original_filename,
        "file_size": len(file_data),
        **(metadata or {}),
    }

    relative_path = store_file(project_id, entity_id, evidence_type, file_data, filename)

    result = CaptureResult(
        success=True, url="",
        evidence_paths=[relative_path],
        metadata=meta,
        duration_ms=int((time.time() - start) * 1000),
    )

    if db:
        ev_id = db.add_evidence(
            entity_id=entity_id,
            evidence_type=evidence_type,
            file_path=relative_path,
            source_name=source_name,
            metadata=meta,
        )
        result.evidence_ids.append(ev_id)

    return result

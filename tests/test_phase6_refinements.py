"""Tests for Phase 6: UI/UX Refinement, Accessibility, and Reliability."""
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC = REPO_ROOT / "app" / "static"
TEMPLATES = REPO_ROOT / "app" / "templates"


def test_phase6_health_endpoint(client):
    """Health check confirms Phase 6 and version 0.6.0."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["phase"] == 6
    assert data["version"] == "0.6.0"


def test_dashboard_contains_phase6_ui_elements(client):
    """Dashboard HTML renders all Phase 6 accessibility and reliability elements."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Mode badge & processing indicator
    assert 'id="recognition-mode-badge"' in html
    assert 'id="processing-indicator"' in html

    # 2. Multi-face breakdown container
    assert 'id="faces-detail-container"' in html
    assert 'id="faces-detail-list"' in html

    # 3. Phase 6 banner announcement
    assert "Phase 6" in html


def test_base_template_footer_updated_to_phase6(client):
    """Base template includes Phase 6 accessible description."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Phase 6" in html
    assert "100% locally" in html


def test_css_includes_phase6_styles():
    """styles.css contains styling rules for processing indicator and face detail cards."""
    css_path = STATIC / "css" / "styles.css"
    content = css_path.read_text(encoding="utf-8")

    assert ".processing-indicator" in content
    assert ".faces-detail-container" in content
    assert ".faces-detail-list" in content
    assert ".face-detail-card" in content


def test_recognition_js_includes_abort_and_stale_request_guards():
    """recognition.js must use AbortController and activeRequestId for stale request protection."""
    js_path = STATIC / "js" / "recognition.js"
    content = js_path.read_text(encoding="utf-8")

    assert "AbortController" in content
    assert "activeRequestId" in content
    assert "activeAbortController" in content
    assert "signal: abortController.signal" in content
    assert "facesDetailContainer" in content
    assert "facesDetailList" in content
    assert "recognitionModeBadge" in content
    assert "processingIndicator" in content


def test_camera_js_invariant_preserved():
    """camera.js must preserve Phase 1 boundaries: strictly camera management only."""
    camera_js = (STATIC / "js" / "camera.js").read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", camera_js, flags=re.S)  # ignore comments
    assert not re.search(r"\bfetch\s*\(", code)
    assert not re.search(r"\bXMLHttpRequest\b", code)
    assert not re.search(r"\bcanvas\b", code, re.I)
    assert not re.search(r"speechSynthesis", code)

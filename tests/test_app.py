import re
from pathlib import Path

import pytest
from flask import Flask

from app import create_app
from app.config import Config, TestingConfig

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"


# ---- Application initialisation ------------------------------------------

def test_create_app_returns_flask_app(app):
    assert isinstance(app, Flask)
    assert app.config["TESTING"] is True


def test_default_config_is_safe():
    assert Config.DEBUG is False
    assert Config.HOST == "127.0.0.1"
    assert Config.SECRET_KEY and len(Config.SECRET_KEY) >= 32
    assert Config.MAX_CONTENT_LENGTH <= 10 * 1024 * 1024


def test_expected_routes_registered(app):
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert {"/", "/register", "/manage", "/api/health"} <= rules


def test_app_factory_gives_independent_instances():
    assert create_app(TestingConfig) is not create_app(TestingConfig)


# ---- Health endpoint ------------------------------------------------------

def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.mimetype == "application/json"
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["app"] == "AI Person Recognition"
    assert body["phase"] == 7
    assert body["version"] == "1.0.0"
    assert {"version", "timestamp", "python", "capabilities"} <= body.keys()


def test_health_reports_phase7_capabilities(client):
    caps = client.get("/api/health").get_json()["capabilities"]
    assert caps["camera_preview"] is True
    assert caps["database"] is True
    assert caps["face_detection"] is True
    assert caps["face_recognition"] is True
    assert caps["expression_analysis"] is True
    assert caps["speech_feedback"] is True


def test_health_rejects_post_with_json_405(client):
    resp = client.post("/api/health")
    assert resp.status_code == 405
    assert resp.mimetype == "application/json"
    assert resp.get_json()["error"]["code"] == 405


def test_health_head_allowed(client):
    assert client.head("/api/health").status_code == 200


# ---- Dashboard and pages --------------------------------------------------

def test_dashboard_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "<h1" in html and "AI Person Recognition" in html
    assert '<html lang="en">' in html
    assert 'id="main"' in html and 'class="skip-link"' in html


def test_dashboard_has_camera_controls_and_status_region(client):
    html = client.get("/").get_data(as_text=True)
    assert 'id="start-camera"' in html and "Start camera" in html
    assert 'id="stop-camera"' in html and "Stop camera" in html
    assert 'id="recognize-btn"' in html and "Recognize Face" in html
    assert 'id="camera-overlay"' in html
    assert re.search(r'id="camera-status"[^>]*role="status"', html)
    assert re.search(r'id="camera-error"[^>]*role="alert"', html)
    assert "<video" in html and 'aria-label="Live camera preview"' in html


def test_dashboard_navigation(client):
    html = client.get("/").get_data(as_text=True)
    assert '<nav aria-label="Main">' in html
    for label in ("Dashboard", "Register Person", "Manage People"):
        assert label in html
    assert 'aria-current="page"' in html


def test_dashboard_renders_active_modules(client):
    html = client.get("/").get_data(as_text=True)
    assert "Speech feedback" in html and "Recognition results" in html
    assert "mute-speech-btn" in html and "repeat-speech-btn" in html


def test_register_page_renders(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Register Person" in html
    assert 'id="register-form"' in html
    assert 'id="person-name"' in html
    assert 'id="person-image"' in html
    assert 'id="consent-checkbox"' in html
    assert "Biometric Data &amp; Privacy Notice" in html


def test_manage_page_renders(client):
    resp = client.get("/manage")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Manage People" in html
    assert 'id="search-input"' in html
    assert 'id="people-grid"' in html
    assert 'id="edit-modal"' in html
    assert 'id="delete-modal"' in html


def test_no_inline_scripts_or_styles(client):
    # Required by the Content-Security-Policy (script-src 'self').
    for path in ("/", "/register", "/manage"):
        html = client.get(path).get_data(as_text=True)
        assert not re.search(r"<script(?![^>]*\bsrc=)", html)
        assert "style=" not in html
        assert not re.search(r"\son\w+=", html)


def test_static_assets_served(client):
    assert client.get("/static/css/styles.css").status_code == 200
    assert client.get("/static/js/camera.js").status_code == 200
    assert client.get("/static/js/register.js").status_code == 200
    assert client.get("/static/js/manage.js").status_code == 200
    assert client.get("/static/js/recognition.js").status_code == 200




# ---- Error handling -------------------------------------------------------

def test_unknown_page_returns_html_404(client):
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    assert resp.mimetype == "text/html"
    assert "not found" in resp.get_data(as_text=True).lower()


def test_unknown_api_route_returns_json_404(client):
    resp = client.get("/api/nope")
    assert resp.status_code == 404
    assert resp.mimetype == "application/json"
    body = resp.get_json()
    assert body["status"] == "error" and body["error"]["code"] == 404


def test_unexpected_exception_returns_generic_500(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/api/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    resp = app.test_client().get("/api/boom")
    assert resp.status_code == 500
    assert resp.mimetype == "application/json"
    assert "secret internal detail" not in resp.get_data(as_text=True)


def test_oversized_request_rejected(app):
    app.config["MAX_CONTENT_LENGTH"] = 10

    @app.post("/api/echo")
    def echo():
        from flask import request
        return request.get_data()

    resp = app.test_client().post("/api/echo", data=b"x" * 100)
    assert resp.status_code == 413
    assert resp.get_json()["error"]["code"] == 413


# ---- Privacy / security headers ------------------------------------------

def test_security_headers_present(client):
    h = client.get("/").headers
    assert "script-src 'self'" in h["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["Referrer-Policy"] == "no-referrer"
    assert "camera=(self)" in h["Permissions-Policy"]
    assert "microphone=()" in h["Permissions-Policy"]


def test_dynamic_responses_not_cached(client):
    assert client.get("/").headers["Cache-Control"] == "no-store"
    assert client.get("/api/health").headers["Cache-Control"] == "no-store"


def test_camera_script_never_transmits_or_captures_frames():
    js = (STATIC / "js" / "camera.js").read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)  # ignore comments
    for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon",
                      "canvas", "toDataURL", "toBlob", "localStorage", "indexedDB",
                      "MediaRecorder", "ImageCapture"):
        assert forbidden not in code, f"camera.js must not use {forbidden}"
    assert "audio: false" in js


def test_camera_requested_only_on_click():
    js = (STATIC / "js" / "camera.js").read_text(encoding="utf-8")
    # getUserMedia is called inside startCamera only, which is bound to the click.
    assert js.count("getUserMedia(") == 1
    assert "addEventListener('click', startCamera)" in js

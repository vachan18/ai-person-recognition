"""Comprehensive tests for Phase 5: Live Recognition and Voice Feedback."""
import base64
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static"


def test_health_reports_all_phase5_capabilities_true(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["phase"] >= 5
    assert body["version"] in ("0.5.0", "0.6.0", "1.0.0")

    caps = body["capabilities"]
    assert caps["camera_preview"] is True
    assert caps["database"] is True
    assert caps["face_detection"] is True
    assert caps["face_recognition"] is True
    assert caps["expression_analysis"] is True
    assert caps["speech_feedback"] is True


def test_dashboard_renders_phase5_speech_controls(client):
    html = client.get("/").get_data(as_text=True)

    # Core elements
    assert 'id="speech-heading"' in html
    assert 'id="speech-status-badge"' in html
    assert 'id="latest-announcement-text"' in html

    # Action buttons
    assert 'id="mute-speech-btn"' in html
    assert 'aria-pressed="false"' in html
    assert 'id="repeat-speech-btn"' in html

    # Settings selects
    assert 'id="speech-rate-select"' in html
    assert 'id="speech-cooldown-select"' in html

    # Accessible aria attributes
    assert 'aria-labelledby="speech-heading"' in html
    assert "Spoken announcements describe visible facial cues as probabilistic estimates" in html


def test_camera_script_preserves_hardware_isolation():
    """Confirms camera.js remains strictly isolated to webcam stream lifecycle."""
    js = (STATIC / "js" / "camera.js").read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
    for forbidden in (
        "fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon",
        "canvas", "toDataURL", "toBlob", "SpeechSynthesis", "speechSynthesis"
    ):
        assert forbidden not in code, f"camera.js must not use {forbidden}"


def test_recognition_script_implements_speech_and_cooldown():
    """Confirms recognition.js implements client-side Web Speech synthesis and duplicate suppression."""
    js = (STATIC / "js" / "recognition.js").read_text(encoding="utf-8")

    # Speech Synthesis APIs
    assert "speechSynthesis" in js
    assert "SpeechSynthesisUtterance" in js
    assert "speakAnnouncement" in js
    assert "cancelSpeech" in js

    # Duplicate suppression and cooldown
    assert "speechCooldownSelect" in js
    assert "speechRateSelect" in js
    assert "previousPeopleInScene" in js
    assert "lastSpokenMessage" in js
    assert "lastSpokenTime" in js

    # Controlled loop backpressure
    assert "isProcessing" in js
    assert "setInterval" in js


def test_api_payload_readiness_for_voice_feedback(client, sample_face_bytes):
    b64_img = f"data:image/jpeg;base64,{base64.b64encode(sample_face_bytes).decode('utf-8')}"
    resp = client.post("/api/recognize", json={"image": b64_img})
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["status"] == "ok"
    assert data["faces_count"] == 1

    face = data["faces"][0]
    # Check structure needed for natural speech generator:
    assert "status" in face  # "recognized" / "uncertain" / "unknown"
    assert "name" in face
    assert "expression" in face
    assert "label" in face["expression"]
    assert "status" in face["expression"]

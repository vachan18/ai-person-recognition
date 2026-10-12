"""Comprehensive tests for Phase 4 Facial Expression Classification."""
import base64
import cv2
import numpy as np
import pytest

from app.services.expressions import (
    EXPRESSION_LABELS,
    ExpressionClassifier,
    ModelNotLoadedError,
    get_expression_classifier,
)
from app.services.face_detector import get_face_detector
from app.services.recognition_service import RecognitionService


# ---- Model Initialization & Error Handling -------------------------------

def test_fer_missing_model_raises_error(tmp_path):
    fake_path = str(tmp_path / "missing_fer_model.onnx")
    with pytest.raises(ModelNotLoadedError) as exc:
        ExpressionClassifier(model_path=fake_path)
    assert "not found" in str(exc.value).lower()


def test_fer_labels_are_universal_seven():
    labels = ExpressionClassifier.labels()
    assert len(labels) == 7
    expected = ["angry", "disgust", "fearful", "happy", "neutral", "sad", "surprised"]
    assert sorted(labels) == sorted(expected)


# ---- Face Expression Inference & Landmark Alignment ----------------------

def test_classify_face_on_valid_image(app, sample_face_bytes):
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        detector = get_face_detector()
        faces = detector.detect_faces(img_bgr)
        assert len(faces) >= 1

        face_info = faces[0]
        classifier = get_expression_classifier()

        res = classifier.classify_face(
            img_bgr, landmarks=face_info["landmarks"], box=face_info["box"]
        )

        assert res["status"] in {"classified", "uncertain"}
        assert res["label"] in EXPRESSION_LABELS or res["label"] == "uncertain"
        assert isinstance(res["confidence"], float)
        assert 0.0 <= res["confidence"] <= 1.0

        # Check probability distribution across all 7 classes
        assert "scores" in res
        assert len(res["scores"]) == 7
        for label in EXPRESSION_LABELS:
            assert label in res["scores"]
            assert 0.0 <= res["scores"][label] <= 1.0

        scores_sum = sum(res["scores"].values())
        assert abs(scores_sum - 1.0) < 0.02  # Sums to ~1.0 with rounding


def test_classify_face_crop_directly(app, sample_face_bytes):
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        detector = get_face_detector()
        faces = detector.detect_faces(img_bgr)
        assert len(faces) >= 1

        box = faces[0]["box"]
        crop = img_bgr[box["y"]:box["y"] + box["height"], box["x"]:box["x"] + box["width"]]

        classifier = get_expression_classifier()
        res = classifier.classify_crop(crop)

        assert res["status"] == "classified"
        assert res["label"] in EXPRESSION_LABELS
        assert res["confidence"] > 0.4


# ---- Unusable & Invalid Inputs --------------------------------------------

def test_fer_rejects_none_or_empty_inputs(app):
    with app.app_context():
        classifier = get_expression_classifier()

        res_none = classifier.classify_face(None)
        assert res_none["status"] == "unusable"
        assert res_none["label"] == "unusable"
        assert res_none["confidence"] == 0.0

        empty_img = np.zeros((0, 0, 3), dtype=np.uint8)
        res_empty = classifier.classify_crop(empty_img)
        assert res_empty["status"] == "unusable"


def test_fer_rejects_non_3channel_images(app):
    with app.app_context():
        classifier = get_expression_classifier()
        single_channel = np.zeros((112, 112), dtype=np.uint8)
        res = classifier.classify_crop(single_channel)
        assert res["status"] == "unusable"
        assert "3-channel" in res["warning"]


def test_fer_rejects_tiny_degraded_crops(app):
    with app.app_context():
        classifier = get_expression_classifier()
        tiny_crop = np.zeros((10, 10, 3), dtype=np.uint8)
        res = classifier.classify_crop(tiny_crop)
        assert res["status"] == "unusable"
        assert "too small" in res["warning"].lower()


# ---- Uncertainty Handling -------------------------------------------------

def test_fer_marks_uncertain_when_confidence_below_threshold(app, sample_face_bytes):
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Create a classifier instance with an impossibly strict threshold of 0.999
        strict_classifier = ExpressionClassifier(confidence_threshold=0.999)
        res = strict_classifier.classify_face(img_bgr)

        assert res["status"] == "uncertain"
        assert res["label"] == "uncertain"
        assert "candidate" in res
        assert res["candidate"] in EXPRESSION_LABELS


# ---- Robust Error Handling Without Crashing -------------------------------

def test_fer_handles_inference_exceptions_gracefully(app, sample_face_bytes, monkeypatch):
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        classifier = get_expression_classifier()

        def mock_blob(*args, **kwargs):
            raise RuntimeError("Simulated DNN blob preprocessing failure")

        monkeypatch.setattr(cv2.dnn, "blobFromImage", mock_blob)

        res = classifier.classify_face(img_bgr)
        assert res["status"] == "unusable"
        assert "Simulated DNN blob preprocessing failure" in res["warning"]


# ---- Pipeline and API Integration -----------------------------------------

def test_recognition_service_attaches_expression_data(app, sample_face_bytes):
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        result = RecognitionService.recognize_faces(img_bgr)
        assert result["status"] == "ok"
        assert result["faces_count"] == 1

        face = result["faces"][0]
        assert "expression" in face
        expr = face["expression"]
        assert expr["status"] in {"classified", "uncertain"}
        assert expr["label"] in EXPRESSION_LABELS
        assert "confidence" in expr
        assert "scores" in expr


def test_api_recognize_returns_structured_expression_results(client, sample_face_bytes):
    b64_img = f"data:image/jpeg;base64,{base64.b64encode(sample_face_bytes).decode('utf-8')}"
    resp = client.post("/api/recognize", json={"image": b64_img})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["faces_count"] == 1

    face = data["faces"][0]
    assert "expression" in face
    assert face["expression"]["status"] == "classified"
    assert face["expression"]["label"] in EXPRESSION_LABELS
    assert len(face["expression"]["scores"]) == 7

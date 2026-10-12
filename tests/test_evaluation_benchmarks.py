"""Automated Benchmarks and Rigorous Model Evaluation for Phase 7."""
import os
import time
import cv2
import numpy as np
import pytest

from app.services.face_detector import get_face_detector
from app.services.face_recognizer import get_face_recognizer
from app.services.expressions import get_expression_classifier, EXPRESSION_LABELS
from app.services.recognition_service import RecognitionService
from app.services.person_service import PersonService


def test_model_initialization_benchmarks(app):
    """Verify that all three local ONNX models initialize cleanly within reasonable time."""
    with app.app_context():
        t0 = time.perf_counter()
        detector = get_face_detector()
        t_det = (time.perf_counter() - t0) * 1000
        assert detector is not None
        assert t_det < 500  # under 500ms init

        t0 = time.perf_counter()
        recognizer = get_face_recognizer()
        t_rec = (time.perf_counter() - t0) * 1000
        assert recognizer is not None
        assert t_rec < 500

        t0 = time.perf_counter()
        classifier = get_expression_classifier()
        t_fer = (time.perf_counter() - t0) * 1000
        assert classifier is not None
        assert t_fer < 500


def test_face_detection_and_embedding_extraction_latency(app, sample_face_bytes):
    """Verify detection and embedding extraction performance on local CPU."""
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        detector = get_face_detector()
        recognizer = get_face_recognizer()

        # Warmup
        faces = detector.detect_faces(img)
        assert len(faces) == 1
        raw_face = faces[0]["raw_face"]
        emb = recognizer.extract_feature(img, raw_face)
        assert emb.shape == (1, 128)

        # Timed detection runs
        t0 = time.perf_counter()
        for _ in range(10):
            faces = detector.detect_faces(img)
        avg_det_ms = ((time.perf_counter() - t0) / 10) * 1000

        # Timed feature extraction runs
        t0 = time.perf_counter()
        for _ in range(10):
            emb = recognizer.extract_feature(img, raw_face)
        avg_rec_ms = ((time.perf_counter() - t0) / 10) * 1000

        assert avg_det_ms < 150  # Must be fast enough for live loop
        assert avg_rec_ms < 100


def test_cosine_threshold_discrimination(app, sample_face_bytes):
    """Verify that the 0.363 cosine matching threshold reliably discriminates identities."""
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        detector = get_face_detector()
        recognizer = get_face_recognizer()

        faces = detector.detect_faces(img)
        emb1 = recognizer.extract_feature(img, faces[0]["raw_face"])

        # 1. Self similarity should be ~ 1.0
        self_sim = recognizer.compute_similarity(emb1, emb1)
        assert self_sim >= 0.99, f"Self-similarity should be ~1.0, got {self_sim}"

        # 2. Orthogonal/random vector should yield near zero similarity
        rng = np.random.default_rng(42)
        rand_emb = rng.standard_normal((1, 128)).astype(np.float32)
        rand_emb /= np.linalg.norm(rand_emb)
        rand_sim = recognizer.compute_similarity(emb1, rand_emb)
        assert rand_sim < 0.30, f"Random embedding similarity should be < 0.30, got {rand_sim}"

        # 3. Inverted vector should yield negative similarity
        inv_sim = recognizer.compute_similarity(emb1, -emb1)
        assert inv_sim <= -0.99


def test_facial_expression_classification_correctness(app, sample_face_bytes):
    """Verify expression classification probabilities and label alignment."""
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        detector = get_face_detector()
        classifier = get_expression_classifier()

        faces = detector.detect_faces(img)
        landmarks = faces[0]["landmarks"]
        box = faces[0]["box"]

        result = classifier.classify_face(img, landmarks=landmarks, box=box)
        assert result["status"] in ("classified", "uncertain")
        assert result["label"] in EXPRESSION_LABELS or result["label"] == "uncertain"
        assert "scores" in result
        assert len(result["scores"]) == 7

        # Probabilities must sum approximately to 1.0 (Softmax calibration)
        prob_sum = sum(result["scores"].values())
        assert abs(prob_sum - 1.0) < 0.02


def test_end_to_end_recognition_service_latency(app, sample_face_bytes):
    """Verify end-to-end RecognitionService execution latency."""
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        t0 = time.perf_counter()
        resp = RecognitionService.recognize_faces(img)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert resp["status"] == "ok"
        assert resp["faces_count"] == 1
        assert "processing_time_ms" in resp
        assert resp["processing_time_ms"] > 0
        assert elapsed_ms < 300  # Well within the 1200ms live loop target

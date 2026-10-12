"""Comprehensive tests for YuNet face detection, SFace recognition, and the /api/recognize endpoint."""
import base64
import io
import cv2
import numpy as np
import pytest

from app.db import get_db
from app.services.face_detector import FaceDetector, ModelNotLoadedError, get_face_detector
from app.services.face_recognizer import FaceRecognizer, get_face_recognizer
from app.services.recognition_service import RecognitionService


# ---- Model Initialization & Error Handling -------------------------------

def test_face_detector_missing_model_raises_error(tmp_path):
    fake_path = str(tmp_path / "missing_yunet.onnx")
    with pytest.raises(ModelNotLoadedError) as exc:
        FaceDetector(model_path=fake_path)
    assert "not found" in str(exc.value).lower()


def test_face_recognizer_missing_model_raises_error(tmp_path):
    fake_path = str(tmp_path / "missing_sface.onnx")
    with pytest.raises(ModelNotLoadedError) as exc:
        FaceRecognizer(model_path=fake_path)
    assert "not found" in str(exc.value).lower()


# ---- Face Detection ------------------------------------------------------

def test_detect_faces_on_valid_image(app, sample_face_bytes):
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        detector = get_face_detector()
        faces = detector.detect_faces(img_bgr)

        assert len(faces) == 1
        face = faces[0]
        assert "box" in face
        assert face["box"]["width"] > 20
        assert face["box"]["height"] > 20
        assert face["confidence"] > 0.6
        assert len(face["landmarks"]) == 5
        assert face["raw_face"] is not None


def test_detect_faces_on_image_with_no_face(app, sample_image_bytes):
    with app.app_context():
        nparr = np.frombuffer(sample_image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        detector = get_face_detector()
        faces = detector.detect_faces(img_bgr)
        assert len(faces) == 0


def test_detect_faces_rejects_invalid_inputs(app):
    with app.app_context():
        detector = get_face_detector()
        with pytest.raises(ValueError):
            detector.detect_faces(None)
        with pytest.raises(ValueError):
            detector.detect_faces(np.zeros((100, 100), dtype=np.uint8))  # 1-channel


# ---- Embedding Extraction & Numerical Validation -------------------------

def test_extract_embedding_properties(app, sample_face_bytes):
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        detector = get_face_detector()
        faces = detector.detect_faces(img_bgr)
        assert len(faces) >= 1

        recognizer = get_face_recognizer()
        embedding = recognizer.extract_feature(img_bgr, faces[0]["raw_face"])

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (1, 128)
        assert embedding.dtype == np.float32
        assert not np.isnan(embedding).any()
        assert not np.isinf(embedding).any()

        # Self-similarity should be ~1.0
        self_sim = recognizer.compute_similarity(embedding, embedding)
        assert self_sim > 0.99


# ---- Multiple Faces Handling ---------------------------------------------

def test_multiple_faces_detected_in_composite_image(app, sample_face_bytes):
    with app.app_context():
        nparr = np.frombuffer(sample_face_bytes, np.uint8)
        face1 = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # Create a side-by-side composite with two faces
        h, w = face1.shape[:2]
        composite = np.zeros((h, w * 2, 3), dtype=np.uint8)
        composite[:, :w] = face1
        composite[:, w:] = face1

        detector = get_face_detector()
        faces = detector.detect_faces(composite)
        assert len(faces) >= 2


# ---- End-to-End Recognition API & Database Consistency ------------------

def test_recognize_api_empty_gallery_returns_unknown(client, sample_face_bytes):
    # Probing when no persons are registered in database
    resp = client.post(
        "/api/recognize",
        data={"image": (io.BytesIO(sample_face_bytes), "probe.jpg")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["faces_count"] == 1
    face_result = data["faces"][0]
    assert face_result["status"] == "unknown"
    assert face_result["person_id"] is None
    assert face_result["name"] == "Unknown"
    assert data["processing_time_ms"] > 0


def test_recognize_api_registered_person_success(client, sample_face_bytes, app):
    # 1. Register a person
    reg_resp = client.post(
        "/api/persons",
        data={
            "name": "Grace Hopper",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "grace.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.get_json()
    person_id = reg_data["person"]["id"]

    # Verify embedding stored in database
    with app.app_context():
        db = get_db()
        emb_row = db.execute(
            "SELECT * FROM face_embeddings WHERE person_id = ?", (person_id,)
        ).fetchone()
        assert emb_row is not None
        assert len(emb_row["embedding"]) == 128 * 4  # 128 float32 = 512 bytes
        assert emb_row["model_name"] == "SFace"

    # 2. Probe with same face via base64 JSON
    b64_str = base64.b64encode(sample_face_bytes).decode("ascii")
    probe_resp = client.post(
        "/api/recognize",
        json={"image": f"data:image/jpeg;base64,{b64_str}"},
    )
    assert probe_resp.status_code == 200
    probe_data = probe_resp.get_json()
    assert probe_data["faces_count"] == 1
    match = probe_data["faces"][0]
    assert match["status"] == "recognized"
    assert match["person_id"] == person_id
    assert match["name"] == "Grace Hopper"
    assert match["similarity"] > 0.8  # same face yields high similarity score


def test_recognize_api_no_faces_detected(client, sample_image_bytes):
    # Submit solid colored square
    resp = client.post(
        "/api/recognize",
        data={"image": (io.BytesIO(sample_image_bytes), "blank.jpg")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["faces_count"] == 0
    assert data["faces"] == []


def test_recognize_api_rejects_empty_payload(client):
    resp = client.post("/api/recognize", json={})
    assert resp.status_code == 400
    assert "no image provided" in resp.get_json()["error"]["message"].lower()


def test_recognize_api_rejects_corrupted_image(client):
    resp = client.post(
        "/api/recognize",
        data={"image": (io.BytesIO(b"corrupt non-image data"), "corrupt.jpg")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_deletion_cascades_and_removes_embeddings(client, sample_face_bytes, app):
    reg_resp = client.post(
        "/api/persons",
        data={
            "name": "Delete Me",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "face.jpg"),
        },
        content_type="multipart/form-data",
    )
    person_id = reg_resp.get_json()["person"]["id"]

    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM face_embeddings WHERE person_id = ?", (person_id,)).fetchone()[0] == 1

    # Delete person
    del_resp = client.delete(f"/api/persons/{person_id}")
    assert del_resp.status_code == 200

    # Confirm embeddings removed
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM face_embeddings WHERE person_id = ?", (person_id,)).fetchone()[0] == 0

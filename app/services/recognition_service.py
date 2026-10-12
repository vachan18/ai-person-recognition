"""Recognition pipeline combining face detection, embedding extraction, and identity matching."""
import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np
from flask import current_app

from app.services.expressions import ExpressionClassifier, get_expression_classifier
from app.services.face_detector import FaceDetector, get_face_detector
from app.services.face_recognizer import FaceRecognizer, get_face_recognizer
from app.services.person_service import PersonService

log = logging.getLogger(__name__)


class RecognitionService:
    """Orchestrates face detection, identity recognition, and expression analysis."""

    @classmethod
    def recognize_faces(
        cls,
        image_bgr: np.ndarray,
        cosine_threshold: Optional[float] = None,
        uncertain_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Detect all faces in image_bgr, match each against registered persons,
        and classify visible facial expressions.

        Returns a structured dictionary with detected faces, matching identities,
        expression categories, similarities, bounding boxes, and processing duration.
        """
        start_time = time.perf_counter()

        if cosine_threshold is None:
            cosine_threshold = current_app.config.get("RECOGNITION_COSINE_THRESHOLD", 0.363)
        if uncertain_threshold is None:
            uncertain_threshold = current_app.config.get("RECOGNITION_UNCERTAIN_LOWER", 0.30)

        detector = get_face_detector()
        recognizer = get_face_recognizer()
        exp_classifier = get_expression_classifier()

        # 1. Detect all faces in frame
        detected_faces = detector.detect_faces(image_bgr)
        if not detected_faces:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "ok",
                "faces_count": 0,
                "faces": [],
                "processing_time_ms": duration_ms,
                "message": "No faces detected in the provided image.",
            }

        # 2. Retrieve registered gallery embeddings
        registered_people = PersonService.get_all_registered_embeddings()

        results: List[Dict[str, Any]] = []

        # 3. Process each detected face independently
        for face_info in detected_faces:
            box = face_info["box"]
            detect_confidence = face_info["confidence"]
            raw_face = face_info["raw_face"]
            landmarks = face_info.get("landmarks")

            # A. Independent facial expression classification
            try:
                expression_info = exp_classifier.classify_face(
                    image_bgr, landmarks=landmarks, box=box
                )
            except Exception as exc:
                log.warning("Expression classification error: %s", exc)
                expression_info = {
                    "status": "unusable",
                    "label": "unusable",
                    "confidence": 0.0,
                    "scores": {},
                    "warning": "Expression classification failed.",
                }

            # B. Independent identity feature extraction and matching
            try:
                probe_embedding = recognizer.extract_feature(image_bgr, raw_face)
            except Exception as exc:
                log.warning("Feature extraction failed for a detected face: %s", exc)
                results.append(
                    {
                        "box": box,
                        "detection_confidence": detect_confidence,
                        "status": "unknown",
                        "person_id": None,
                        "name": "Unknown",
                        "similarity": 0.0,
                        "expression": expression_info,
                        "warning": "Could not align face for recognition.",
                    }
                )
                continue

            # Compare probe against registered gallery
            best_person_id: Optional[int] = None
            best_person_name: Optional[str] = None
            highest_similarity: float = -1.0

            for candidate in registered_people:
                sim = recognizer.compute_similarity(probe_embedding, candidate["embedding"])
                if sim > highest_similarity:
                    highest_similarity = sim
                    best_person_id = candidate["person_id"]
                    best_person_name = candidate["name"]

            # Classification based on validated threshold
            # SFace cosine threshold: >= 0.363 -> recognized
            # between 0.30 and 0.363 -> uncertain
            # < 0.30 -> unknown
            sim_rounded = round(max(0.0, highest_similarity), 4)

            if registered_people and highest_similarity >= cosine_threshold:
                face_status = "recognized"
                matched_id = best_person_id
                matched_name = best_person_name
            elif registered_people and highest_similarity >= uncertain_threshold:
                face_status = "uncertain"
                matched_id = None
                matched_name = "Uncertain"
            else:
                face_status = "unknown"
                matched_id = None
                matched_name = "Unknown"

            results.append(
                {
                    "box": box,
                    "detection_confidence": detect_confidence,
                    "status": face_status,
                    "person_id": matched_id,
                    "name": matched_name,
                    "similarity": sim_rounded,
                    "expression": expression_info,
                }
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "ok",
            "faces_count": len(results),
            "faces": results,
            "processing_time_ms": duration_ms,
        }

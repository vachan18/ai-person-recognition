"""Face feature extraction and similarity comparison using OpenCV Zoo SFace ONNX model."""
import logging
import os
from typing import Optional

import cv2
import numpy as np
from flask import current_app

from app.services.face_detector import ModelNotLoadedError

log = logging.getLogger(__name__)


class FaceRecognizer:
    """Wraps cv2.FaceRecognizerSF for face alignment, feature extraction, and cosine matching."""

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self._recognizer: Optional[cv2.FaceRecognizerSF] = None
        self._load_model()

    def _load_model(self) -> None:
        if not os.path.isfile(self.model_path):
            raise ModelNotLoadedError(
                f"Face recognition model file not found at '{self.model_path}'. "
                "Ensure local ONNX weights exist before running inference."
            )
        try:
            self._recognizer = cv2.FaceRecognizerSF.create(self.model_path, "")
            log.info("SFace face recognizer successfully initialized from %s", self.model_path)
        except Exception as exc:
            raise ModelNotLoadedError(
                f"Failed to load SFace model from '{self.model_path}': {exc}"
            ) from exc

    def extract_feature(self, image_bgr: np.ndarray, raw_face: np.ndarray) -> np.ndarray:
        """Align a detected face crop and extract a 128-dimensional L2-normalized embedding.

        Args:
            image_bgr: Source image in BGR format.
            raw_face: 15-element numpy array produced by YuNet detection.

        Returns:
            128-dimensional float32 numpy array of shape (1, 128).
        """
        if self._recognizer is None:
            raise ModelNotLoadedError("FaceRecognizer is not initialized.")

        if image_bgr is None or raw_face is None:
            raise ValueError("image_bgr and raw_face must not be None.")

        # 1. Align and crop face
        aligned_face = self._recognizer.alignCrop(image_bgr, raw_face)
        if aligned_face is None or aligned_face.size == 0:
            raise ValueError("Face alignment failed on the provided face coordinates.")

        # 2. Extract feature representation (128-d float32)
        feature = self._recognizer.feature(aligned_face)

        if feature is None or not isinstance(feature, np.ndarray):
            raise ValueError("Feature extraction returned an invalid result.")

        if feature.shape != (1, 128) and feature.shape != (128,):
            raise ValueError(f"Unexpected embedding shape: {feature.shape}, expected (1, 128).")

        # Normalize shape to (1, 128) float32
        feature = feature.reshape(1, 128).astype(np.float32)

        # Validate numerical integrity
        if np.isnan(feature).any() or np.isinf(feature).any():
            raise ValueError("Generated facial embedding contains NaN or Inf values.")

        return feature

    def compute_similarity(self, feature1: np.ndarray, feature2: np.ndarray) -> float:
        """Compute cosine similarity score between two facial embeddings.

        Higher score indicates higher similarity. SFace cosine threshold is ~0.363.
        """
        if self._recognizer is None:
            raise ModelNotLoadedError("FaceRecognizer is not initialized.")

        f1 = feature1.reshape(1, 128).astype(np.float32)
        f2 = feature2.reshape(1, 128).astype(np.float32)

        try:
            # OpenCV FaceRecognizerSF_FR_COSINE comparison
            score = self._recognizer.match(f1, f2, cv2.FaceRecognizerSF_FR_COSINE)
            return float(score)
        except Exception:
            # Fallback to standard numpy cosine similarity
            norm1 = np.linalg.norm(f1)
            norm2 = np.linalg.norm(f2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(np.dot(f1[0], f2[0]) / (norm1 * norm2))


_recognizer_instance: Optional[FaceRecognizer] = None


def get_face_recognizer() -> FaceRecognizer:
    """Return a shared singleton instance of FaceRecognizer."""
    global _recognizer_instance
    if _recognizer_instance is None:
        model_path = current_app.config["SFACE_MODEL_PATH"]
        _recognizer_instance = FaceRecognizer(model_path=model_path)
    return _recognizer_instance

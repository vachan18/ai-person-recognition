"""Face detection service using OpenCV Zoo YuNet ONNX model."""
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from flask import current_app

log = logging.getLogger(__name__)


class ModelNotLoadedError(RuntimeError):
    """Raised when an ONNX model file is missing or cannot be loaded by OpenCV."""
    pass


class FaceDetector:
    """Wraps cv2.FaceDetectorYN for fast local face detection."""

    def __init__(
        self,
        model_path: str,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3,
    ) -> None:
        self.model_path = model_path
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self._detector: Optional[cv2.FaceDetectorYN] = None
        self._load_model()

    def _load_model(self) -> None:
        if not os.path.isfile(self.model_path):
            raise ModelNotLoadedError(
                f"Face detection model file not found at '{self.model_path}'. "
                "Ensure local ONNX weights exist before running inference."
            )
        try:
            self._detector = cv2.FaceDetectorYN.create(
                self.model_path,
                "",
                (320, 320),
                score_threshold=self.score_threshold,
                nms_threshold=self.nms_threshold,
            )
            log.info("YuNet face detector successfully initialized from %s", self.model_path)
        except Exception as exc:
            raise ModelNotLoadedError(
                f"Failed to load YuNet model from '{self.model_path}': {exc}"
            ) from exc

    def detect_faces(
        self,
        image_bgr: np.ndarray,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Detect faces in a BGR image.

        Returns a list of dictionaries with bounding box, confidence, landmarks,
        and raw face representation needed for face alignment.
        """
        if self._detector is None:
            raise ModelNotLoadedError("FaceDetector is not initialized.")

        if image_bgr is None or not isinstance(image_bgr, np.ndarray):
            raise ValueError("Input image must be a valid numpy ndarray.")

        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError(f"Image must have 3 channels (BGR). Got shape {image_bgr.shape}.")

        h, w = image_bgr.shape[:2]
        if h < 20 or w < 20:
            return []

        # Set dynamic input size for the current image
        self._detector.setInputSize((w, h))
        if score_threshold is not None:
            self._detector.setScoreThreshold(score_threshold)
        else:
            self._detector.setScoreThreshold(self.score_threshold)

        _, faces = self._detector.detect(image_bgr)
        if faces is None:
            return []

        results = []
        for face in faces:
            # face elements:
            # 0: x, 1: y, 2: w, 3: h
            # 4-13: 5 landmarks (x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm)
            # 14: score
            x = int(face[0])
            y = int(face[1])
            box_w = int(face[2])
            box_h = int(face[3])
            score = float(face[14])

            # Extract 5 facial landmarks
            landmarks = [
                (float(face[4]), float(face[5])),   # Right eye
                (float(face[6]), float(face[7])),   # Left eye
                (float(face[8]), float(face[9])),   # Nose tip
                (float(face[10]), float(face[11])), # Right mouth corner
                (float(face[12]), float(face[13])), # Left mouth corner
            ]

            results.append(
                {
                    "box": {
                        "x": max(0, x),
                        "y": max(0, y),
                        "width": max(1, box_w),
                        "height": max(1, box_h),
                    },
                    "confidence": round(score, 4),
                    "landmarks": landmarks,
                    "raw_face": face,
                }
            )

        return results


_detector_instance: Optional[FaceDetector] = None


def get_face_detector() -> FaceDetector:
    """Return a shared singleton instance of FaceDetector."""
    global _detector_instance
    if _detector_instance is None:
        model_path = current_app.config["YUNET_MODEL_PATH"]
        score_thresh = current_app.config.get("YUNET_SCORE_THRESHOLD", 0.6)
        nms_thresh = current_app.config.get("YUNET_NMS_THRESHOLD", 0.3)
        _detector_instance = FaceDetector(
            model_path=model_path,
            score_threshold=score_thresh,
            nms_threshold=nms_thresh,
        )
    return _detector_instance

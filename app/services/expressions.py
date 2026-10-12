"""Facial Expression Classification service using OpenCV Zoo MobileFaceNet.

Implements local, privacy-preserving facial emotion estimation (7 universal expressions)
paired with face detection and landmark alignment. Does not use external AI services.
"""
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
from flask import current_app, g
import numpy as np

log = logging.getLogger(__name__)


class ModelNotLoadedError(RuntimeError):
    """Raised when the FER model file cannot be found or loaded."""


class ExpressionAnalysisError(RuntimeError):
    """Raised when facial expression classification fails unexpectedly."""


# Canonical 7 basic facial emotion classes supported by MobileFaceNet / Progressive Teacher
EXPRESSION_LABELS: List[str] = [
    "angry",
    "disgust",
    "fearful",
    "happy",
    "neutral",
    "sad",
    "surprised",
]

# Standard 5 facial landmark anchor points for 112x112 aligned face crop
# Coordinates corresponding to: [right eye, left eye, nose tip, right mouth corner, left mouth corner]
STD_LANDMARKS_112: np.ndarray = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


class ExpressionClassifier:
    """Classifies visible facial expressions using OpenCV Zoo MobileFaceNet in ONNX format."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.45,
        min_face_size: int = 24,
    ):
        if model_path is None:
            if current_app:
                model_path = current_app.config.get("FER_MODEL_PATH")
            else:
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                model_path = os.path.join(
                    base_dir, "models", "facial_expression_recognition_mobilefacenet_2022july.onnx"
                )

        if not model_path or not os.path.isfile(model_path):
            raise ModelNotLoadedError(
                f"Facial expression model not found at path: {model_path}. "
                "Please ensure facial_expression_recognition_mobilefacenet_2022july.onnx exists in models/."
            )

        self.model_path = model_path
        self.confidence_threshold = float(confidence_threshold)
        self.min_face_size = int(min_face_size)

        try:
            self._net = cv2.dnn.readNetFromONNX(self.model_path)
            self._net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self._net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        except Exception as exc:
            raise ModelNotLoadedError(f"Failed to load FER model from {model_path}: {exc}") from exc

        log.info("Initialized ExpressionClassifier with model: %s", self.model_path)

    @classmethod
    def labels(cls) -> List[str]:
        """Return the list of supported expression categories."""
        return list(EXPRESSION_LABELS)

    def align_and_crop(
        self,
        image_bgr: np.ndarray,
        landmarks: Optional[Union[np.ndarray, List[List[float]]]] = None,
        box: Optional[Dict[str, int]] = None,
    ) -> Optional[np.ndarray]:
        """Align face using 5 facial landmarks or crop using bounding box, resized to 112x112."""
        if image_bgr is None or not isinstance(image_bgr, np.ndarray) or image_bgr.size == 0:
            return None

        # Try landmark-based similarity affine alignment first
        if landmarks is not None:
            try:
                lm = np.asarray(landmarks, dtype=np.float32)
                if lm.shape == (5, 2):
                    tfm, _ = cv2.estimateAffinePartial2D(lm, STD_LANDMARKS_112)
                    if tfm is not None:
                        aligned = cv2.warpAffine(
                            image_bgr,
                            tfm,
                            (112, 112),
                            borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(0, 0, 0),
                        )
                        return aligned
            except Exception as exc:
                log.debug("Landmark-based alignment failed, falling back to box crop: %s", exc)

        # Fallback to bounding box crop
        img_h, img_w = image_bgr.shape[:2]
        if box is not None and isinstance(box, dict):
            bx = max(0, int(box.get("x", 0)))
            by = max(0, int(box.get("y", 0)))
            bw = int(box.get("width", 0))
            bh = int(box.get("height", 0))

            if bw < self.min_face_size or bh < self.min_face_size:
                return None

            bx2 = min(img_w, bx + bw)
            by2 = min(img_h, by + bh)

            if bx2 <= bx or by2 <= by:
                return None

            crop = image_bgr[by:by2, bx:bx2]
        else:
            # Entire image provided as crop
            crop = image_bgr

        if crop.shape[0] < self.min_face_size or crop.shape[1] < self.min_face_size:
            return None

        return cv2.resize(crop, (112, 112), interpolation=cv2.INTER_LINEAR)

    def classify_crop(self, face_crop_bgr: np.ndarray) -> Dict[str, Any]:
        """Perform preprocessing and inference on an already isolated/aligned face image."""
        if face_crop_bgr is None or not isinstance(face_crop_bgr, np.ndarray):
            return {
                "status": "unusable",
                "label": "unusable",
                "confidence": 0.0,
                "scores": {},
                "warning": "Input face image is missing or invalid.",
            }

        if len(face_crop_bgr.shape) != 3 or face_crop_bgr.shape[2] != 3:
            return {
                "status": "unusable",
                "label": "unusable",
                "confidence": 0.0,
                "scores": {},
                "warning": "Input face image must be a 3-channel BGR image.",
            }

        h, w = face_crop_bgr.shape[:2]
        if h < self.min_face_size or w < self.min_face_size:
            return {
                "status": "unusable",
                "label": "unusable",
                "confidence": 0.0,
                "scores": {},
                "warning": f"Face region is too small ({w}x{h} px) for reliable classification.",
            }

        try:
            # 1. Resize to 112x112 if not already
            if (w, h) != (112, 112):
                face_crop_bgr = cv2.resize(face_crop_bgr, (112, 112), interpolation=cv2.INTER_LINEAR)

            # 2. Preprocess: BGR -> RGB, float32, scale to [0, 1], normalize with mean=0.5, std=0.5
            rgb = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            norm_img = (rgb - 0.5) / 0.5

            # 3. Create 4D Blob
            blob = cv2.dnn.blobFromImage(norm_img)

            # 4. Forward pass
            self._net.setInput(blob, "data")
            raw_output = self._net.forward("label")

            logits = raw_output[0].flatten()

            # 5. Softmax probability calculation
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / np.sum(exp_logits)

            # 6. Build structured score distribution
            scores: Dict[str, float] = {}
            for idx, label in enumerate(EXPRESSION_LABELS):
                scores[label] = round(float(probs[idx]), 4)

            top_idx = int(np.argmax(probs))
            top_label = EXPRESSION_LABELS[top_idx]
            top_conf = round(float(probs[top_idx]), 4)

            # 7. Check confidence threshold for uncertain classification
            if top_conf < self.confidence_threshold:
                return {
                    "status": "uncertain",
                    "label": "uncertain",
                    "candidate": top_label,
                    "confidence": top_conf,
                    "scores": scores,
                }

            return {
                "status": "classified",
                "label": top_label,
                "candidate": top_label,
                "confidence": top_conf,
                "scores": scores,
            }

        except Exception as exc:
            log.warning("Exception during expression classification: %s", exc)
            return {
                "status": "unusable",
                "label": "unusable",
                "confidence": 0.0,
                "scores": {},
                "warning": f"Inference error: {str(exc)}",
            }

    def classify_face(
        self,
        image_bgr: np.ndarray,
        landmarks: Optional[Union[np.ndarray, List[List[float]]]] = None,
        box: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """Classify facial expression from a full camera frame or cropped face."""
        if image_bgr is None or not isinstance(image_bgr, np.ndarray):
            return {
                "status": "unusable",
                "label": "unusable",
                "confidence": 0.0,
                "scores": {},
                "warning": "Missing or invalid image input.",
            }

        aligned_crop = self.align_and_crop(image_bgr, landmarks=landmarks, box=box)
        if aligned_crop is None:
            return {
                "status": "unusable",
                "label": "unusable",
                "confidence": 0.0,
                "scores": {},
                "warning": "Face crop could not be extracted or is below minimum resolution.",
            }

        return self.classify_crop(aligned_crop)


def get_expression_classifier() -> ExpressionClassifier:
    """Retrieve or initialize the thread/app-local ExpressionClassifier singleton."""
    if current_app:
        if "expression_classifier" not in g:
            threshold = current_app.config.get("FER_CONFIDENCE_THRESHOLD", 0.45)
            min_size = current_app.config.get("FER_MIN_FACE_SIZE", 24)
            g.expression_classifier = ExpressionClassifier(
                confidence_threshold=threshold,
                min_face_size=min_size,
            )
        return g.expression_classifier

    return ExpressionClassifier()

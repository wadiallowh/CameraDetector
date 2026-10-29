
from pathlib import Path

import cv2
import numpy as np

from trusted_faces import load_registry
from config_manager import load_config


BASE_DIR = Path(__file__).resolve().parent

YUNET_MODEL = (
    BASE_DIR / "models"
    / "face_detection_yunet_2023mar.onnx"
)

SFACE_MODEL = (
    BASE_DIR / "models"
    / "face_recognition_sface_2021dec.onnx"
)

# Conservative starting threshold.
# Tune using real trusted/unknown comparisons.
MATCH_THRESHOLD = 0.50


class FaceRecognitionEngine:

    def __init__(self):
        config = load_config()

        self.score_threshold = float(
            config.get("yunet_score_threshold", 0.90)
        )

        if not 0.50 <= self.score_threshold <= 0.99:
            raise ValueError(
                "YuNet score threshold must be between "
                "0.50 and 0.99."
            )

        self.detector = cv2.FaceDetectorYN.create(
            str(YUNET_MODEL),
            "",
            (320, 320),
            score_threshold=self.score_threshold,
            nms_threshold=0.3,
            top_k=5000
        )
        self.reload_trusted_faces()

    def reload_trusted_faces(self):
        self.registry = {}

        for name, embeddings in load_registry().items():
            self.registry[name] = [
                np.asarray(
                    embedding,
                    dtype=np.float32
                ).reshape(1, -1)
                for embedding in embeddings
            ]

    def recognize(self, frame):
        height, width = frame.shape[:2]

        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(frame)

        results = []

        if faces is None:
            return results

        for face in faces:
            aligned = self.recognizer.alignCrop(
                frame, face
            )

            embedding = self.recognizer.feature(
                aligned
            )

            best_name = None
            best_score = -1.0

            for name, reference_embeddings in self.registry.items():
                for reference in reference_embeddings:
                    score = self.recognizer.match(
                        embedding,
                        reference,
                        cv2.FaceRecognizerSF_FR_COSINE
                    )

                    if score > best_score:
                        best_score = score
                        best_name = name

            trusted = (
                best_name is not None
                and best_score >= MATCH_THRESHOLD
            )

            x, y, w, h = map(int, face[:4])

            results.append({
                "name": best_name if trusted else "Unknown",
                "trusted": trusted,
                "score": float(best_score),
                "box": (x, y, w, h)
            })

        return results


"""
CameraDetector - Face Recognition Engine

YuNet: Face detection
SFace: Face recognition

YuNet detection threshold is configurable through
config.json using "yunet_score_threshold".

SFace identity matching uses MATCH_THRESHOLD.
"""

from pathlib import Path
import math

import cv2
import numpy as np

from config_manager import load_config
from trusted_faces import load_registry


# ==========================================
# PATHS AND SETTINGS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

YUNET_MODEL = (
    MODELS_DIR / "face_detection_yunet_2023mar.onnx"
)

SFACE_MODEL = (
    MODELS_DIR / "face_recognition_sface_2021dec.onnx"
)

DEFAULT_YUNET_THRESHOLD = 0.90

# SFace cosine similarity threshold.
# Separate from YuNet detection sensitivity.
MATCH_THRESHOLD = 0.50


# ==========================================
# FACE RECOGNITION ENGINE
# ==========================================

class FaceRecognitionEngine:

    def __init__(self):

        # ----------------------------------
        # Load configuration
        # ----------------------------------

        config = load_config()

        self.score_threshold = float(
            config.get(
                "yunet_score_threshold",
                DEFAULT_YUNET_THRESHOLD
            )
        )

        if (
            not math.isfinite(self.score_threshold)
            or not 0.50 <= self.score_threshold <= 0.99
        ):
            raise ValueError(
                "YuNet score threshold must be "
                "between 0.50 and 0.99."
            )

        self.match_threshold = MATCH_THRESHOLD

        # ----------------------------------
        # Verify models exist
        # ----------------------------------

        if not YUNET_MODEL.is_file():
            raise FileNotFoundError(
                f"YuNet model not found: {YUNET_MODEL}\n"
                "Run: python download_models.py"
            )

        if not SFACE_MODEL.is_file():
            raise FileNotFoundError(
                f"SFace model not found: {SFACE_MODEL}\n"
                "Run: python download_models.py"
            )

        # ----------------------------------
        # Initialize YuNet face detector
        # ----------------------------------

        self.detector = cv2.FaceDetectorYN.create(
            str(YUNET_MODEL),
            "",
            (320, 320),
            score_threshold=self.score_threshold,
            nms_threshold=0.3,
            top_k=5000
        )

        # ----------------------------------
        # Initialize SFace recognizer
        # ----------------------------------

        self.recognizer = cv2.FaceRecognizerSF.create(
            str(SFACE_MODEL),
            ""
        )

        # ----------------------------------
        # Load registered trusted faces
        # ----------------------------------

        self.trusted_faces = {}
        self.reload_trusted_faces()

    # ======================================
    # REGISTRY HANDLING
    # ======================================

    @staticmethod
    def _normalize_embedding(value):
        """
        Convert a stored feature vector to a
        float32 NumPy array compatible with SFace.
        """

        try:
            embedding = np.asarray(
                value,
                dtype=np.float32
            ).reshape(1, -1)

            if embedding.shape[1] != 128:
                return None

            if not np.isfinite(embedding).all():
                return None

            return embedding

        except (TypeError, ValueError):
            return None

    def _extract_embeddings(self, record):
        """
        Support lists of embeddings and common
        dictionary-based registry records.
        """

        if isinstance(record, dict):
            for key in (
                "embeddings",
                "features",
                "samples",
                "embedding",
                "feature"
            ):
                if key in record:
                    return self._extract_embeddings(
                        record[key]
                    )

            return []

        if isinstance(record, np.ndarray):
            record = record.tolist()

        if not isinstance(record, (list, tuple)):
            return []

        # A single 128-dimensional embedding
        if (
            len(record) == 128
            and all(
                isinstance(value, (int, float))
                for value in record
            )
        ):
            embedding = self._normalize_embedding(
                record
            )
            return (
                [embedding]
                if embedding is not None
                else []
            )

        # Multiple embeddings
        embeddings = []

        for item in record:
            embeddings.extend(
                self._extract_embeddings(item)
            )

        return embeddings

    def reload_trusted_faces(self):
        """
        Reload registered faces from local storage.

        Existing registrations are not modified.
        """

        registry = load_registry()

        trusted = {}

        if isinstance(registry, dict):

            # Support a wrapped registry structure
            if (
                "people" in registry
                and isinstance(
                    registry["people"],
                    (dict, list)
                )
            ):
                registry = registry["people"]

            if isinstance(registry, dict):
                entries = registry.items()
            else:
                entries = []

        elif isinstance(registry, list):
            entries = []

            for person in registry:
                if isinstance(person, dict):
                    name = person.get("name")

                    if name:
                        entries.append(
                            (name, person)
                        )
        else:
            entries = []

        for name, record in entries:

            if not isinstance(name, str):
                continue

            embeddings = self._extract_embeddings(
                record
            )

            if embeddings:
                trusted[name] = embeddings

        self.trusted_faces = trusted
        # Compatibility with detector.py
        self.registry = self.trusted_faces

        return len(self.trusted_faces)

    # ======================================
    # FACE DETECTION
    # ======================================

    def detect_faces(self, frame):
        """
        Detect faces using YuNet.

        Returns raw YuNet face detections.
        """

        if frame is None:
            return []

        if not isinstance(frame, np.ndarray):
            return []

        if frame.size == 0:
            return []

        height, width = frame.shape[:2]

        if height <= 0 or width <= 0:
            return []

        self.detector.setInputSize(
            (width, height)
        )

        _, faces = self.detector.detect(frame)

        if faces is None:
            return []

        return faces

    # ======================================
    # FEATURE EXTRACTION
    # ======================================

    def extract_embedding(self, frame, face):
        """
        Align a detected face and extract its
        128-dimensional SFace embedding.
        """

        aligned = self.recognizer.alignCrop(
            frame,
            face
        )

        embedding = self.recognizer.feature(
            aligned
        )

        return self._normalize_embedding(
            embedding
        )

    # ======================================
    # IDENTITY COMPARISON
    # ======================================

    def identify_face(self, embedding):
        """
        Compare an embedding against trusted
        people using SFace cosine similarity.

        Returns:
            name, similarity, is_trusted
        """

        best_name = "Unknown"
        best_similarity = -1.0

        if embedding is None:
            return (
                best_name,
                best_similarity,
                False
            )

        for name, stored_embeddings in (
            self.trusted_faces.items()
        ):

            for stored in stored_embeddings:

                similarity = float(
                    self.recognizer.match(
                        embedding,
                        stored,
                        cv2.FaceRecognizerSF_FR_COSINE
                    )
                )

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_name = name

        is_trusted = (
            best_similarity
            >= self.match_threshold
        )

        if not is_trusted:
            best_name = "Unknown"

        return (
            best_name,
            best_similarity,
            is_trusted
        )

    # ======================================
    # COMPLETE RECOGNITION PIPELINE
    # ======================================

    def recognize(self, frame):
        """
        Detect and recognize faces in a frame.

        Returns a list of face-result dictionaries.

        Face coordinates are expressed in pixels
        relative to the input frame.
        """

        results = []

        faces = self.detect_faces(frame)

        for face in faces:

            x = int(face[0])
            y = int(face[1])
            width = int(face[2])
            height = int(face[3])

            # YuNet detection confidence
            detection_score = float(face[14])

            # Extract SFace features
            embedding = self.extract_embedding(
                frame,
                face
            )

            # Match against trusted faces
            (
                name,
                similarity,
                is_trusted
            ) = self.identify_face(
                embedding
            )

            result = {
                "name": name,
                "trusted": is_trusted,
                "is_trusted": is_trusted,
                "similarity": similarity,
                "score": detection_score,
                "detection_score": detection_score,
                "box": (
                    x,
                    y,
                    width,
                    height
                ),
                "bbox": (
                    x,
                    y,
                    width,
                    height
                )
            }

            results.append(result)

        return results


# ==========================================
# DIRECT MODULE TEST
# ==========================================

if __name__ == "__main__":

    print("Initializing face recognition engine...")

    engine = FaceRecognitionEngine()

    print("[OK] YuNet initialized.")
    print(
        "[OK] YuNet threshold:",
        engine.score_threshold
    )

    print("[OK] SFace initialized.")
    print(
        "[OK] Identity matching threshold:",
        engine.match_threshold
    )

    print(
        "[OK] Registered trusted people:",
        len(engine.trusted_faces)
    )

    print("Face recognition engine ready.")


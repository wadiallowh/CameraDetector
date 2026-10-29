
import cv2
import time
from pathlib import Path

from config_manager import load_config
from trusted_faces import register_person, list_people


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

YUNET_MODEL = (
    BASE_DIR / "models" /
    "face_detection_yunet_2023mar.onnx"
)

SFACE_MODEL = (
    BASE_DIR / "models" /
    "face_recognition_sface_2021dec.onnx"
)

SAMPLES_REQUIRED = 10
SAMPLE_INTERVAL = 0.8
MIN_FACE_WIDTH = 100
WINDOW_NAME = "CameraDetector - Face Registration"


# ==========================================
# REGISTRATION
# ==========================================

def main():

    print("\n=== TRUSTED FACE REGISTRATION ===")

    name = input("Enter person's name: ").strip()

    if not name:
        print("Name cannot be empty.")
        return

    if name in list_people():
        print("This person is already registered.")
        return

    consent = input(
        "Does this person agree to face enrollment? (y/n): "
    ).strip().lower()

    if consent != "y":
        print("Registration cancelled.")
        return

    config = load_config()
    camera_index = config["camera_index"]

    detector = cv2.FaceDetectorYN.create(
        str(YUNET_MODEL),
        "",
        (320, 320),
        score_threshold=0.9,
        nms_threshold=0.3,
        top_k=5000
    )

    recognizer = cv2.FaceRecognizerSF.create(
        str(SFACE_MODEL),
        ""
    )

    camera = cv2.VideoCapture(
        camera_index,
        cv2.CAP_DSHOW
    )

    if not camera.isOpened():
        print("Cannot open webcam.")
        print("Stop the running CameraDetector first.")
        camera.release()
        return

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        config["camera_width"]
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        config["camera_height"]
    )

    embeddings = []
    last_sample_time = 0

    print("\nLook toward the camera.")
    print("Slowly vary your angle and expression.")
    print("Press Q or ESC to cancel registration.")

    try:
        while len(embeddings) < SAMPLES_REQUIRED:

            success, frame = camera.read()

            if not success:
                print("Failed to read camera frame.")
                break

            height, width = frame.shape[:2]
            detector.setInputSize((width, height))

            _, faces = detector.detect(frame)

            display = frame.copy()
            status = "Position one face in front of camera"

            if faces is not None and len(faces) == 1:

                face = faces[0]
                x, y, w, h = map(int, face[:4])

                cv2.rectangle(
                    display,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

                if w >= MIN_FACE_WIDTH:

                    status = "Face detected - collecting samples"

                    now = time.monotonic()

                    if now - last_sample_time >= SAMPLE_INTERVAL:

                        try:
                            aligned = recognizer.alignCrop(
                                frame, face
                            )

                            embedding = recognizer.feature(
                                aligned
                            )

                            embeddings.append(
                                embedding.flatten().copy()
                            )

                            last_sample_time = now

                            print(
                                f"Captured sample "
                                f"{len(embeddings)}/{SAMPLES_REQUIRED}"
                            )

                        except cv2.error as error:
                            print(
                                f"Sample skipped: {error}"
                            )

                else:
                    status = "Move closer to the webcam"

            elif faces is not None and len(faces) > 1:
                status = "Multiple faces detected - wait"

            progress = (
                f"Samples: {len(embeddings)}/"
                f"{SAMPLES_REQUIRED}"
            )

            cv2.putText(
                display,
                progress,
                (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            cv2.putText(
                display,
                status,
                (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 255, 255),
                2
            )

            preview_width = 800
            preview_height = int(
                height * preview_width / width
            )

            preview = cv2.resize(
                display,
                (preview_width, preview_height)
            )

            cv2.imshow(WINDOW_NAME, preview)

            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), 27):
                print("Registration cancelled.")
                return

        if len(embeddings) == SAMPLES_REQUIRED:

            register_person(name, embeddings)

            print(
                f"\nSUCCESS: {name} registered with "
                f"{len(embeddings)} face samples."
            )

        else:
            print("Not enough samples. Nothing saved.")

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

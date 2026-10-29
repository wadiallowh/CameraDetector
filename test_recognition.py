
import cv2

from config_manager import load_config
from face_recognition_engine import FaceRecognitionEngine

WINDOW_NAME = "CameraDetector - Recognition Test"
PREVIEW_WIDTH = 800


def main():
    config = load_config()
    engine = FaceRecognitionEngine()

    print("=== LIVE FACE RECOGNITION TEST ===")
    print("Registered people:", list(engine.registry.keys()))
    print("Green = Trusted")
    print("Red = Unknown")
    print("Press Q or ESC to exit.")

    camera = cv2.VideoCapture(
        config["camera_index"],
        cv2.CAP_DSHOW
    )

    if not camera.isOpened():
        print("Cannot access camera.")
        print("Stop CameraDetector before running this test.")
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

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("Failed to read camera frame.")
                break

            results = engine.recognize(frame)

            for result in results:
                x, y, w, h = result["box"]

                color = (
                    (0, 200, 0)
                    if result["trusted"]
                    else (0, 0, 255)
                )

                label = (
                    f"{result['name']} "
                    f"({result['score']:.2f})"
                )

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    color,
                    2
                )

                cv2.putText(
                    frame,
                    label,
                    (x, max(25, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    color,
                    2
                )

            height, width = frame.shape[:2]
            preview_height = int(
                height * PREVIEW_WIDTH / width
            )

            preview = cv2.resize(
                frame,
                (PREVIEW_WIDTH, preview_height),
                interpolation=cv2.INTER_AREA
            )

            cv2.imshow(WINDOW_NAME, preview)

            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()
        print("Recognition test stopped.")


if __name__ == "__main__":
    main()


import hashlib
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"

MODELS = {
    "face_detection_yunet_2023mar.onnx": {
        "url": (
            "https://huggingface.co/opencv/opencv_zoo/"
            "resolve/main/models/face_detection_yunet/"
            "face_detection_yunet_2023mar.onnx"
        ),
        "sha256": (
            "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9"
            "f4280604804ed2552fa4"
        )
    },
    "face_recognition_sface_2021dec.onnx": {
        "url": (
            "https://huggingface.co/opencv/opencv_zoo/"
            "resolve/main/models/face_recognition_sface/"
            "face_recognition_sface_2021dec.onnx"
        ),
        "sha256": (
            "0ba9fbfa01b5270c96627c4ef784da859931e02f04419"
            "c829e83484087c34e79"
        )
    }
}


def calculate_sha256(path):
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def download_model(filename, information):
    destination = MODEL_DIR / filename
    expected_hash = information["sha256"]

    if destination.exists():
        if calculate_sha256(destination) == expected_hash:
            print(f"[OK] {filename} already verified.")
            return True

        print(f"[WARNING] {filename} failed verification.")
        print("A verified replacement will be downloaded.")

    temporary = MODEL_DIR / (filename + ".download")

    try:
        request = urllib.request.Request(
            information["url"],
            headers={
                "User-Agent": "CameraDetector/1.0"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=120
        ) as response:
            with open(temporary, "wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)

                    if not chunk:
                        break

                    output.write(chunk)

        if calculate_sha256(temporary) != expected_hash:
            raise ValueError(
                f"SHA-256 verification failed: {filename}"
            )

        temporary.replace(destination)

        print(f"[OK] {filename} downloaded and verified.")
        return True

    except Exception as error:
        print(f"[ERROR] {filename}: {error}")
        return False

    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 45)
    print("CAMERA DETECTOR - MODEL INSTALLER")
    print("=" * 45)

    successful = True

    for filename, information in MODELS.items():
        if not download_model(filename, information):
            successful = False

    if successful:
        print("\nAll face recognition models are ready.")
    else:
        print("\nSome models could not be installed.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

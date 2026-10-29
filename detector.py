
import cv2
import time
import logging
from pathlib import Path

import win32api
import win32con

from winotify import Notification, audio
from pygrabber.dshow_graph import FilterGraph

from session_monitor import SessionMonitor
from config_manager import load_config
from face_recognition_engine import FaceRecognitionEngine
from logger_manager import get_logger


# ==========================================
# APPLICATION PATHS AND LOGGING
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

logger = get_logger()

WINDOW_NAME = "CameraDetector - Live Monitoring"


# ==========================================
# LOAD CONFIGURATION
# ==========================================

def read_configuration():
    config = load_config()

    return {
        "camera_index": int(config["camera_index"]),
        "camera_width": int(config["camera_width"]),
        "camera_height": int(config["camera_height"]),
        "process_width": int(config["process_width"]),
        "preview_width": int(config["preview_width"]),
        "face_confirmation": float(
            config["face_confirmation"]
        ),
        "notification_cooldown": float(
            config["notification_cooldown"]
        ),
        "minimum_detection_frames": int(
            config.get("minimum_detection_frames", 5)
        ),
        "reconnect_delay": float(
            config["reconnect_delay"]
        ),
        "notifications_enabled": bool(
            config["notifications_enabled"]
        ),
        "preview_on_startup": bool(
            config["preview_on_startup"]
        )
    }


# ==========================================
# CAMERA IDENTIFICATION
# ==========================================

def get_camera_name(index):
    try:
        devices = FilterGraph().get_input_devices()

        if 0 <= index < len(devices):
            return devices[index]

    except Exception:
        logger.exception(
            "Unable to retrieve camera device names."
        )

    return f"Camera {index}"


# ==========================================
# CAMERA CONNECTION
# ==========================================

def open_camera(settings, camera_name):
    index = settings["camera_index"]

    camera = cv2.VideoCapture(
        index,
        cv2.CAP_DSHOW
    )

    if not camera.isOpened():
        camera.release()
        return None

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        settings["camera_width"]
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        settings["camera_height"]
    )

    actual_width = int(
        camera.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    actual_height = int(
        camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    logger.info(
        "Camera connected: %s | Index: %s | "
        "Resolution: %sx%s",
        camera_name,
        index,
        actual_width,
        actual_height
    )

    print(
        f"[CAMERA] Connected: {camera_name}",
        flush=True
    )

    return camera


# ==========================================
# WINDOWS NOTIFICATIONS
# ==========================================

def send_notification(settings):
    if not settings["notifications_enabled"]:
        logger.info(
            "Unknown face confirmed. "
            "Notifications are disabled."
        )
        return

    try:
        toast = Notification(
            app_id="CameraDetector",
            title="Unknown Person Detected!",
            msg=(
                "CameraDetector has detected "
                "an unrecognized face."
            ),
            duration="short"
        )

        toast.set_audio(
            audio.Default,
            loop=False
        )

        toast.show()

        logger.info(
            "Unknown-face notification requested."
        )

        print(
            "[NOTIFICATION] Notification requested.",
            flush=True
        )

    except Exception:
        logger.exception(
            "Failed to send Windows notification."
        )


# ==========================================
# CAMERA PREVIEW
# ==========================================

def show_preview(
    frame,
    results,
    status,
    settings
):
    display = frame.copy()

    frame_height, frame_width = display.shape[:2]

    scale_x = (
        frame_width / settings["process_width"]
    )

    process_height = int(
        frame_height
        * settings["process_width"]
        / frame_width
    )

    scale_y = frame_height / process_height

    # Draw recognized and unknown faces
    for result in results:
        x, y, w, h = result["box"]

        x1 = int(x * scale_x)
        y1 = int(y * scale_y)

        x2 = int((x + w) * scale_x)
        y2 = int((y + h) * scale_y)

        if result["trusted"]:
            color = (0, 255, 0)
            label = result["name"]
        else:
            color = (0, 0, 255)
            label = "UNKNOWN"

        cv2.rectangle(
            display,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        cv2.putText(
            display,
            label,
            (x1, max(25, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2
        )

    # Draw monitoring status
    cv2.putText(
        display,
        status,
        (20, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    preview_width = settings["preview_width"]

    preview_height = int(
        frame_height * preview_width / frame_width
    )

    preview = cv2.resize(
        display,
        (preview_width, preview_height),
        interpolation=cv2.INTER_AREA
    )

    cv2.imshow(WINDOW_NAME, preview)
    cv2.waitKey(1)

    # Detect when the user closes the preview
    try:
        visible = cv2.getWindowProperty(
            WINDOW_NAME,
            cv2.WND_PROP_VISIBLE
        )

        return visible >= 1

    except cv2.error:
        return False


# ==========================================
# MAIN CAMERA DETECTOR
# ==========================================

def main():
    camera = None
    session = None
    preview_enabled = False

    logger.info("=" * 45)
    logger.info("CameraDetector starting.")

    try:
        # ==================================
        # INITIALIZE CONFIGURATION
        # ==================================

        settings = read_configuration()

        camera_index = settings["camera_index"]

        camera_name = get_camera_name(
            camera_index
        )

        preview_enabled = settings[
            "preview_on_startup"
        ]

        logger.info(
            "Selected camera: %s (Index %s)",
            camera_name,
            camera_index
        )

        # ==================================
        # INITIALIZE RECOGNITION
        # ==================================

        recognition_engine = FaceRecognitionEngine()

        logger.info(
            "Face recognition initialized. "
            "Trusted identities loaded: %s",
            len(recognition_engine.registry)
        )

        # ==================================
        # INITIALIZE SESSION MONITOR
        # ==================================

        session = SessionMonitor()
        session.start()

        logger.info(
            "Windows session monitoring started."
        )

        # ==================================
        # DETECTION STATE
        # ==================================

        unknown_start_time = None
        consecutive_unknown_frames = 0
        unknown_confirmed = False

        last_alert_time = float("-inf")

        was_locked = False
        camera_unavailable_logged = False

        print("=" * 45)
        print("       CAMERA DETECTOR")
        print("=" * 45)
        print(f"Camera: {camera_name}")
        print(f"Camera index: {camera_index}")
        print(
            "Face confirmation:",
            settings["face_confirmation"]
        )
        print(
            "Minimum detection frames:",
            settings["minimum_detection_frames"]
        )
        print(
            "Notification cooldown:",
            settings["notification_cooldown"]
        )
        print("Face recognition: Enabled")
        print("F8: Show / Hide preview")
        print("Ctrl+C: Stop monitoring")
        print("=" * 45)

        logger.info(
            "CameraDetector initialization completed."
        )

        # ==================================
        # MAIN LOOP
        # ==================================

        while True:

            # ==================================
            # WINDOWS LOCK HANDLING
            # ==================================

            if session.is_locked:

                if not was_locked:
                    logger.info(
                        "Windows locked. Pausing monitoring."
                    )
                    was_locked = True

                if camera is not None:
                    camera.release()
                    camera = None

                    logger.info(
                        "Camera released due to Windows lock."
                    )

                unknown_start_time = None
                consecutive_unknown_frames = 0
                unknown_confirmed = False

                if preview_enabled:
                    cv2.destroyAllWindows()
                    preview_enabled = False

                time.sleep(0.1)
                continue

            if was_locked:
                logger.info(
                    "Windows unlocked. Resuming monitoring."
                )

                was_locked = False

                unknown_start_time = None
                consecutive_unknown_frames = 0
                unknown_confirmed = False

            # ==================================
            # F8 PREVIEW CONTROL
            # ==================================

            if win32api.GetAsyncKeyState(
                win32con.VK_F8
            ) & 1:

                preview_enabled = not preview_enabled

                if preview_enabled:
                    logger.info(
                        "Camera preview enabled."
                    )
                else:
                    cv2.destroyAllWindows()

                    logger.info(
                        "Camera preview hidden."
                    )

            # ==================================
            # CAMERA CONNECTION
            # ==================================

            if camera is None:

                camera = open_camera(
                    settings,
                    camera_name
                )

                if camera is None:

                    if not camera_unavailable_logged:
                        logger.warning(
                            "Camera unavailable: %s "
                            "(Index %s). Retrying.",
                            camera_name,
                            camera_index
                        )

                        camera_unavailable_logged = True

                    time.sleep(
                        settings["reconnect_delay"]
                    )
                    continue

                camera_unavailable_logged = False

            # ==================================
            # READ CAMERA FRAME
            # ==================================

            success, frame = camera.read()

            if not success:
                logger.error(
                    "Camera frame capture failed: %s",
                    camera_name
                )

                camera.release()
                camera = None

                unknown_start_time = None
                consecutive_unknown_frames = 0
                unknown_confirmed = False

                time.sleep(
                    settings["reconnect_delay"]
                )
                continue

            # Check session again before processing
            if session.is_locked:
                continue

            # ==================================
            # RESIZE FRAME
            # ==================================

            height, width = frame.shape[:2]

            process_height = int(
                height
                * settings["process_width"]
                / width
            )

            small_frame = cv2.resize(
                frame,
                (
                    settings["process_width"],
                    process_height
                ),
                interpolation=cv2.INTER_AREA
            )

            # ==================================
            # FACE RECOGNITION
            # ==================================

            try:
                results = recognition_engine.recognize(
                    small_frame
                )

            except Exception:
                logger.exception(
                    "Face recognition processing failed."
                )

                unknown_start_time = None
                consecutive_unknown_frames = 0
                unknown_confirmed = False

                time.sleep(0.1)
                continue

            current_time = time.monotonic()

            trusted_faces = [
                result
                for result in results
                if result["trusted"]
            ]

            unknown_faces = [
                result
                for result in results
                if not result["trusted"]
            ]

            status = "MONITORING - NO FACE"

            # ==================================
            # UNKNOWN FACE CONFIRMATION
            # ==================================

            if unknown_faces:

                consecutive_unknown_frames += 1

                if unknown_start_time is None:
                    unknown_start_time = current_time

                elapsed = (
                    current_time - unknown_start_time
                )

                enough_frames = (
                    consecutive_unknown_frames
                    >= settings["minimum_detection_frames"]
                )

                enough_time = (
                    elapsed
                    >= settings["face_confirmation"]
                )

                if enough_frames and enough_time:

                    status = "UNKNOWN FACE CONFIRMED"

                    if not unknown_confirmed:
                        unknown_confirmed = True

                        if (
                            current_time - last_alert_time
                            >= settings["notification_cooldown"]
                        ):

                            if not session.is_locked:
                                logger.info(
                                    "Unknown face confirmed. "
                                    "Count: %s",
                                    len(unknown_faces)
                                )

                                last_alert_time = current_time

                                send_notification(settings)

                else:
                    status = (
                        f"VERIFYING UNKNOWN: {elapsed:.1f}s "
                        f"| {consecutive_unknown_frames}/"
                        f"{settings['minimum_detection_frames']} "
                        "frames"
                    )

            else:
                unknown_start_time = None
                consecutive_unknown_frames = 0
                unknown_confirmed = False

                if trusted_faces:
                    status = "TRUSTED FACE - NO ALERT"

            # ==================================
            # OPTIONAL PREVIEW
            # ==================================

            if preview_enabled:

                preview_open = show_preview(
                    frame,
                    results,
                    status,
                    settings
                )

                if not preview_open:
                    preview_enabled = False
                    cv2.destroyAllWindows()

                    logger.info(
                        "Camera preview closed by user. "
                        "Monitoring continues."
                    )

            else:
                time.sleep(0.01)

    except KeyboardInterrupt:
        logger.info(
            "CameraDetector stopped by user."
        )

    except Exception:
        logger.exception(
            "CameraDetector terminated unexpectedly."
        )
        raise

    finally:

        if camera is not None:
            camera.release()

        cv2.destroyAllWindows()

        if session is not None:
            try:
                session.stop()
            except Exception:
                logger.exception(
                    "Failed to stop session monitor."
                )

        logger.info(
            "CameraDetector shutdown completed."
        )


# ==========================================
# APPLICATION ENTRY POINT
# ==========================================

if __name__ == "__main__":
    main()

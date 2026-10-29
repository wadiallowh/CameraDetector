
import math
import subprocess
import time

import cv2
from pygrabber.dshow_graph import FilterGraph

from config_manager import (
    load_config,
    save_config,
    update_setting
)

from trusted_faces import list_people, remove_person

from log_viewer import (
    view_system_events,
    view_errors,
    view_detections,
    view_camera_events,
    view_session_events,
    show_log_sizes,
    clear_logs
)

from startup_manager import (
    install_startup,
    remove_startup,
    check_startup
)


TASK_NAME = "CameraDetector"

DEFAULT_YUNET_THRESHOLD = 0.90


# ==========================================
# GENERAL UTILITIES
# ==========================================

def pause():
    input("\nPress Enter to continue...")


def heading(title):
    print("\n" + "=" * 48)
    print(title.center(48))
    print("=" * 48)


def task_command(action):
    return subprocess.run(
        ["schtasks", action, "/TN", TASK_NAME],
        capture_output=True,
        text=True,
        errors="replace"
    )


def task_status():
    result = subprocess.run(
        [
            "schtasks", "/Query",
            "/TN", TASK_NAME,
            "/FO", "LIST"
        ],
        capture_output=True,
        text=True,
        errors="replace"
    )

    if result.returncode == 0:
        print(result.stdout)
    else:
        print(
            "Scheduled task unavailable:",
            result.stderr.strip()
        )


def task_is_running():
    result = subprocess.run(
        [
            "schtasks", "/Query",
            "/TN", TASK_NAME,
            "/FO", "LIST"
        ],
        capture_output=True,
        text=True,
        errors="replace"
    )

    if result.returncode != 0:
        return False

    for line in result.stdout.splitlines():
        if line.strip().lower().startswith("status:"):
            return (
                line.split(":", 1)[1].strip().lower()
                == "running"
            )

    return False


# ==========================================
# MONITORING COMMANDS
# ==========================================

def start_monitoring():
    result = task_command("/Run")

    if result.returncode == 0:
        print("Monitoring start requested.")
    else:
        print("Start failed:", result.stderr.strip())


def stop_monitoring():
    result = task_command("/End")

    if result.returncode == 0:
        print("Monitoring stop requested.")
    else:
        print("Stop failed:", result.stderr.strip())


def restart_monitoring():
    print("Restarting CameraDetector...")

    if task_is_running():
        result = task_command("/End")

        if result.returncode != 0:
            print("Stop failed:", result.stderr.strip())
            return

        time.sleep(2)

    start_monitoring()


# ==========================================
# CONFIGURATION HELPERS
# ==========================================

def set_setting(key, value):
    config = load_config()

    if key in config:
        update_setting(key, value)
    else:
        config[key] = value
        save_config(config)


def edit_integer(key, label, minimum, maximum):
    config = load_config()

    heading(label)

    print("Current value:", config.get(key))
    print(f"Allowed range: {minimum} - {maximum}")
    print("Press Enter to cancel.")

    raw = input("\nNew value: ").strip()

    if not raw:
        return

    try:
        value = int(raw)

        if not minimum <= value <= maximum:
            print("Value outside allowed range.")
            return

        set_setting(key, value)

        print("Setting saved successfully.")
        print("Restart monitoring to apply.")

    except ValueError:
        print("Invalid integer.")


def edit_float(key, label, minimum, maximum):
    config = load_config()

    heading(label)

    print("Current value:", config.get(key))
    print(f"Allowed range: {minimum} - {maximum}")
    print("Press Enter to cancel.")

    raw = input("\nNew value: ").strip()

    if not raw:
        return

    try:
        value = float(raw)

        if not math.isfinite(value):
            print("Invalid number.")
            return

        if not minimum <= value <= maximum:
            print("Value outside allowed range.")
            return

        set_setting(key, value)

        print("Setting saved successfully.")
        print("Restart monitoring to apply.")

    except ValueError:
        print("Invalid number.")


# ==========================================
# YUNET SENSITIVITY
# ==========================================

def sensitivity_description(threshold):
    if threshold <= 0.55:
        return "VERY HIGH"
    if threshold <= 0.65:
        return "HIGH"
    if threshold <= 0.75:
        return "MODERATELY HIGH"
    if threshold <= 0.85:
        return "BALANCED"
    if threshold <= 0.92:
        return "STRICT"
    return "VERY STRICT"


def edit_yunet_sensitivity():
    config = load_config()

    current = float(
        config.get(
            "yunet_score_threshold",
            DEFAULT_YUNET_THRESHOLD
        )
    )

    heading("YUNET DETECTION SENSITIVITY")

    print(f"Current threshold: {current:.2f}")
    print(
        "Current sensitivity:",
        sensitivity_description(current)
    )

    print("\n--- SENSITIVITY GUIDE ---")
    print("0.50 = Very High")
    print("0.60 = High")
    print("0.70 = Moderately High")
    print("0.80 = Balanced")
    print("0.90 = Strict")
    print("0.95 = Very Strict")

    print("\nAllowed range: 0.50 - 0.99")
    print("Lower number = Higher sensitivity")
    print("Higher number = Fewer false positives")
    print("\nPress Enter to cancel.")

    raw = input("\nEnter new threshold: ").strip()

    if not raw:
        print("No changes made.")
        return

    try:
        value = float(raw)

        if (
            not math.isfinite(value)
            or not 0.50 <= value <= 0.99
        ):
            print(
                "Invalid threshold. "
                "Allowed range: 0.50 - 0.99"
            )
            return

        value = round(value, 2)

        set_setting(
            "yunet_score_threshold",
            value
        )

        print("\nSensitivity setting saved!")
        print(f"New threshold: {value:.2f}")
        print(
            "Sensitivity:",
            sensitivity_description(value)
        )

        print(
            "\nThe recognition engine must be updated "
            "to read this setting before it takes effect."
        )

    except ValueError:
        print("Invalid number.")


def show_detection_settings():
    config = load_config()

    threshold = float(
        config.get(
            "yunet_score_threshold",
            DEFAULT_YUNET_THRESHOLD
        )
    )

    heading("CURRENT DETECTION SETTINGS")

    print("Detection engine: YuNet + SFace")

    print(
        f"YuNet threshold: {threshold:.2f}"
    )

    print(
        "Sensitivity:",
        sensitivity_description(threshold)
    )

    print(
        "Face confirmation:",
        config["face_confirmation"],
        "seconds"
    )

    print(
        "Minimum detection frames:",
        config.get("minimum_detection_frames", 5)
    )

    print(
        "\nNote: YuNet threshold changes must be "
        "connected to the recognition engine."
    )


# ==========================================
# MONITORING MENU
# ==========================================

def monitoring_menu():
    while True:
        heading("MONITORING CONTROL")

        print("[1] Check monitoring status")
        print("[2] Start monitoring")
        print("[3] Stop monitoring")
        print("[4] Restart monitoring")
        print("[0] Back")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            task_status()
        elif choice == "2":
            start_monitoring()
        elif choice == "3":
            stop_monitoring()
        elif choice == "4":
            restart_monitoring()
        elif choice == "0":
            return
        else:
            print("Invalid option.")

        pause()


# ==========================================
# DETECTION SETTINGS MENU
# ==========================================

def detection_settings_menu():
    while True:
        heading("DETECTION SETTINGS")

        print("[1] Edit YuNet detection sensitivity")
        print("[2] Edit face confirmation time")
        print("[3] Edit minimum detection frames")
        print("[4] View detection settings")
        print("[0] Back")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            edit_yunet_sensitivity()

        elif choice == "2":
            edit_float(
                "face_confirmation",
                "FACE CONFIRMATION TIME",
                0.1,
                10.0
            )

        elif choice == "3":
            edit_integer(
                "minimum_detection_frames",
                "MINIMUM DETECTION FRAMES",
                1,
                30
            )

        elif choice == "4":
            show_detection_settings()

        elif choice == "0":
            return

        else:
            print("Invalid option.")

        pause()


# ==========================================
# TRUSTED FACES MENU
# ==========================================

def trusted_faces_menu():
    while True:
        heading("TRUSTED FACES")

        print("[1] Register trusted person")
        print("[2] View registered people")
        print("[3] Remove trusted person")
        print("[4] Test face recognition")
        print("[0] Back")

        choice = input("\nSelect option: ").strip()

        if choice in ("1", "4"):

            if task_is_running():
                print(
                    "Stop monitoring before using "
                    "the camera for registration/testing."
                )
                pause()
                continue

            confirm = input(
                "Confirm the webcam is available (y/n): "
            ).strip().lower()

            if confirm != "y":
                print("Cancelled.")
                pause()
                continue

            if choice == "1":
                from face_registration import main
                main()
                print(
                    "Restart monitoring to reload "
                    "registered faces."
                )
            else:
                from test_recognition import main
                main()

        elif choice == "2":
            people = list_people()

            if not people:
                print("No trusted people registered.")
            else:
                for index, name in enumerate(people, 1):
                    print(f"[{index}] {name}")

        elif choice == "3":
            people = list_people()

            if not people:
                print("No trusted people registered.")

            else:
                for index, name in enumerate(people, 1):
                    print(f"[{index}] {name}")

                try:
                    index = int(
                        input("Person number to remove: ")
                    )

                    if not 1 <= index <= len(people):
                        print("Invalid selection.")
                    else:
                        name = people[index - 1]

                        confirm = input(
                            f"Remove {name}? (y/n): "
                        ).strip().lower()

                        if confirm == "y":
                            remove_person(name)
                            print(
                                "Person removed. "
                                "Restart monitoring to apply."
                            )

                except ValueError:
                    print("Invalid number.")

        elif choice == "0":
            return

        else:
            print("Invalid option.")

        pause()


# ==========================================
# CAMERA MANAGEMENT
# ==========================================

def scan_cameras():
    print("\nScanning available cameras...")

    devices = FilterGraph().get_input_devices()
    available = []

    for index, name in enumerate(devices):
        camera = cv2.VideoCapture(
            index,
            cv2.CAP_DSHOW
        )

        try:
            if camera.isOpened():
                success, frame = camera.read()

                if success and frame is not None:
                    height, width = frame.shape[:2]

                    available.append(index)

                    print(
                        f"[{index}] {name} "
                        f"({width}x{height})"
                    )
                else:
                    print(
                        f"[{index}] {name} - No video"
                    )
            else:
                print(
                    f"[{index}] {name} - Unavailable"
                )

        finally:
            camera.release()

    if not available:
        print("No available cameras found.")

    return available


def camera_menu():
    while True:
        heading("CAMERA SETTINGS")

        print("[1] Scan available cameras")
        print("[2] Select camera")
        print("[3] View selected camera")
        print("[0] Back")

        choice = input("\nSelect option: ").strip()

        if choice in ("1", "2"):

            if task_is_running():
                print(
                    "Stop monitoring before scanning cameras."
                )
                pause()
                continue

            confirm = input(
                "Confirm no other detector instance "
                "is using the camera (y/n): "
            ).strip().lower()

            if confirm != "y":
                print("Cancelled.")
                pause()
                continue

            try:
                available = scan_cameras()
            except Exception as error:
                print("Camera scan error:", error)
                available = []

            if choice == "2" and available:
                try:
                    index = int(
                        input("Enter camera index: ")
                    )

                    if index not in available:
                        print("Camera unavailable.")
                    else:
                        set_setting(
                            "camera_index",
                            index
                        )

                        print(
                            "Camera saved. "
                            "Restart monitoring to apply."
                        )

                except ValueError:
                    print("Invalid camera index.")

        elif choice == "3":
            config = load_config()

            print(
                "Selected camera index:",
                config["camera_index"]
            )

        elif choice == "0":
            return

        else:
            print("Invalid option.")

        pause()


# ==========================================
# NOTIFICATION SETTINGS
# ==========================================

def notification_menu():
    while True:
        heading("NOTIFICATION SETTINGS")

        print("[1] Enable / Disable notifications")
        print("[2] Edit notification cooldown")
        print("[3] View notification settings")
        print("[0] Back")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            config = load_config()

            enabled = not config[
                "notifications_enabled"
            ]

            set_setting(
                "notifications_enabled",
                enabled
            )

            print(
                "Notifications:",
                "Enabled" if enabled else "Disabled"
            )

            print("Restart monitoring to apply.")

        elif choice == "2":
            edit_float(
                "notification_cooldown",
                "NOTIFICATION COOLDOWN",
                0.0,
                300.0
            )

        elif choice == "3":
            config = load_config()

            print(
                "Notifications enabled:",
                config["notifications_enabled"]
            )

            print(
                "Cooldown:",
                config["notification_cooldown"],
                "seconds"
            )

        elif choice == "0":
            return

        else:
            print("Invalid option.")

        pause()


# ==========================================
# STARTUP MANAGEMENT
# ==========================================

def startup_menu():
    while True:
        heading("STARTUP MANAGEMENT")

        print("[1] Install automatic startup")
        print("[2] Remove automatic startup")
        print("[3] Check startup configuration")
        print("[0] Back")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            install_startup()
        elif choice == "2":
            remove_startup()
        elif choice == "3":
            check_startup()
        elif choice == "0":
            return
        else:
            print("Invalid option.")

        pause()


# ==========================================
# LOGS & DIAGNOSTICS
# ==========================================

def diagnostics_menu():
    while True:
        heading("LOGS & DIAGNOSTICS")

        print("[1] View recent system events")
        print("[2] View recent errors")
        print("[3] View unknown-face detections")
        print("[4] View camera connection history")
        print("[5] View Windows session events")
        print("[6] Check log file sizes")
        print("[7] Log cleanup information")
        print("[8] Check scheduled task status")
        print("[0] Back")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            view_system_events()
        elif choice == "2":
            view_errors()
        elif choice == "3":
            view_detections()
        elif choice == "4":
            view_camera_events()
        elif choice == "5":
            view_session_events()
        elif choice == "6":
            show_log_sizes()
        elif choice == "7":
            clear_logs()
        elif choice == "8":
            task_status()
        elif choice == "0":
            return
        else:
            print("Invalid option.")

        pause()


# ==========================================
# MAIN CONTROL PANEL
# ==========================================

def main():
    while True:
        heading("CAMERA DETECTOR CONTROL PANEL")

        print("[1] Monitoring Control")
        print("[2] Detection Settings")
        print("[3] Trusted Faces")
        print("[4] Camera Settings")
        print("[5] Notification Settings")
        print("[6] Startup Management")
        print("[7] Logs & Diagnostics")
        print("[0] Exit")

        choice = input("\nSelect category: ").strip()

        if choice == "1":
            monitoring_menu()
        elif choice == "2":
            detection_settings_menu()
        elif choice == "3":
            trusted_faces_menu()
        elif choice == "4":
            camera_menu()
        elif choice == "5":
            notification_menu()
        elif choice == "6":
            startup_menu()
        elif choice == "7":
            diagnostics_menu()
        elif choice == "0":
            print("Closing CameraDetector Control Panel.")
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"


def read_logs(filename, keyword=None, limit=30):
    path = LOG_DIR / filename

    if not path.exists():
        print("Log file does not exist yet.")
        return

    lines = path.read_text(
        encoding="utf-8",
        errors="replace"
    ).splitlines()

    if keyword:
        lines = [
            line for line in lines
            if keyword.lower() in line.lower()
        ]

    if not lines:
        print("No matching records found.")
        return

    print("\n" + "=" * 65)

    for line in lines[-limit:]:
        print(line)

    print("=" * 65)


def view_system_events():
    read_logs("detector.log")


def view_errors():
    read_logs("errors.log")


def view_detections():
    read_logs("detector.log", "Unknown face confirmed")


def view_camera_events():
    read_logs("detector.log", "Camera")


def view_session_events():
    read_logs("detector.log", "Windows locked")
    read_logs("detector.log", "Windows unlocked")


def show_log_sizes():
    print("\n--- LOG STORAGE ---")

    if not LOG_DIR.exists():
        print("No logs directory found.")
        return

    total = 0

    for path in sorted(LOG_DIR.glob("*.log*")):
        if path.is_file():
            size = path.stat().st_size
            total += size

            print(
                f"{path.name}: "
                f"{size / 1024:.2f} KB"
            )

    print(f"\nTotal: {total / 1024:.2f} KB")


def clear_logs():
    confirmation = input(
        "Delete all existing log files? (yes/no): "
    ).strip().lower()

    if confirmation != "yes":
        print("Cancelled.")
        return

    print(
        "Stop CameraDetector before clearing logs "
        "to avoid deleting active log files."
    )
    print(
        "Use automatic rotation for routine cleanup."
    )

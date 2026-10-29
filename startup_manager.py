import os
import sys
import subprocess
from pathlib import Path

TASK_NAME = "CameraDetector"
PROJECT_DIR = Path(__file__).resolve().parent

PYTHONW = PROJECT_DIR / ".venv" / "Scripts" / "pythonw.exe"
DETECTOR = PROJECT_DIR / "detector.py"


def run_command(arguments):
    return subprocess.run(
        arguments,
        capture_output=True,
        text=True,
        errors="replace"
    )


def startup_installed():
    result = run_command([
        "schtasks",
        "/Query",
        "/TN",
        TASK_NAME
    ])
    return result.returncode == 0


def install_startup():
    if not PYTHONW.exists():
        print("ERROR: pythonw.exe was not found.")
        print("Expected:", PYTHONW)
        return

    if not DETECTOR.exists():
        print("ERROR: detector.py was not found.")
        return

    if startup_installed():
        print("CameraDetector startup task already exists.")
        print("No changes made.")
        return

    command = f'"{PYTHONW}" "{DETECTOR}"'

    result = run_command([
        "schtasks",
        "/Create",
        "/TN", TASK_NAME,
        "/TR", command,
        "/SC", "ONLOGON",
        "/RU", os.environ.get("USERDOMAIN", "") + "\\"
               + os.environ.get("USERNAME", ""),
        "/IT",
        "/RL", "LIMITED",
        "/DELAY", "0000:30",
        "/F"
    ])

    if result.returncode == 0:
        print("Automatic startup installed successfully.")
        print("CameraDetector will start after Windows sign-in.")
    else:
        print("Startup installation failed.")
        print(result.stderr.strip())


def remove_startup():
    if not startup_installed():
        print("CameraDetector startup is not installed.")
        return

    confirmation = input(
        "Remove CameraDetector automatic startup? (y/n): "
    ).strip().lower()

    if confirmation != "y":
        print("Cancelled.")
        return

    result = run_command([
        "schtasks",
        "/Delete",
        "/TN", TASK_NAME,
        "/F"
    ])

    if result.returncode == 0:
        print("Automatic startup removed.")
        print("Your project files were not deleted.")
    else:
        print("Failed to remove startup.")
        print(result.stderr.strip())


def check_startup():
    if startup_installed():
        print("Automatic startup: INSTALLED")
        print("Task name:", TASK_NAME)
    else:
        print("Automatic startup: NOT INSTALLED")

# CameraDetector

**CameraDetector** is a Windows webcam-monitoring application written in Python. It detects faces with **OpenCV YuNet**, compares them with locally registered trusted faces using **SFace**, and requests a Windows desktop notification when an **unknown face** is confirmed. It includes a CLI control panel for managing webcams, detection settings, trusted identities, notifications, startup, and logs.

> **Project status:** Early release / personal project. Face detection and recognition can produce false positives, false matches, and missed detections. Do not rely on this project as a security-grade identity or access-control system.

## Features

- YuNet face detection with **configurable detection sensitivity** (`yunet_score_threshold`).
- SFace recognition against multiple locally registered, consenting people.
- Windows toast notifications for unknown faces, even when a trusted person is also in view.
- Configurable confirmation duration, minimum consecutive detection frames, and notification cooldown.
- DirectShow webcam enumeration and camera selection.
- Background monitoring with optional preview toggled using **F8**.
- Webcam release when Windows locks and reconnection after unlocking.
- Optional Windows Task Scheduler auto-start, installed and managed through the CLI.
- Local rotating activity and error logs.

## Requirements

- **Windows 11** (the tested platform; other Windows versions have not been verified).
- **Python 3.13** (64-bit recommended).
- A compatible webcam with camera permissions enabled under Windows **Settings → Privacy & security → Camera**.
- Internet access to install dependencies and download the detection/recognition models.

This application depends on Windows-specific components, including DirectShow, `pywin32`, and `winotify`. It is **not currently cross-platform**.

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/wadiallowh/CameraDetector.git
cd CameraDetector
```

Alternatively, download the ZIP from GitHub and extract it.

### 2. Create and activate a virtual environment

**Command Prompt (CMD):**

```cmd
py -3.13 -m venv .venv
.venv\Scripts\activate
```

**PowerShell:**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, CMD is an alternative that does not require changing the PowerShell execution policy.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

Always activate `.venv` before using `python`; otherwise, you may see `ModuleNotFoundError: No module named 'cv2'`.

### 4. Download the models

```powershell
python download_models.py
```

The script retrieves the YuNet detector and SFace recognizer from OpenCV Zoo and checks their SHA-256 hashes. The `.onnx` model files are downloaded locally and are **not included in Git**.

### 5. Select a camera

```powershell
python control.py
```

Go to **Camera Settings**, scan the available cameras, and select the desired index. Stop monitoring first so the webcam is available for scanning. The local `config.json` is created automatically from `config.example.json` on first use.

## Usage

### Control panel

```powershell
python control.py
```

| Menu | Purpose |
| --- | --- |
| Monitoring Control | Check, start, stop, and restart the scheduled monitoring task |
| Detection Settings | Adjust YuNet sensitivity, face confirmation time, and minimum detection frames |
| Trusted Faces | Register, list, remove, and test trusted people |
| Camera Settings | Find and select the webcam |
| Notification Settings | Enable/disable notifications and set cooldown |
| Startup Management | Install, remove, and check the Windows logon task |
| Logs & Diagnostics | Inspect activity, errors, camera/session events, and log sizes |

**Configuration changes require restarting the monitoring process.** Exiting the CLI does not stop monitoring that was launched separately by Task Scheduler.

### Run manually

With monitoring stopped in the control panel, run:

```powershell
python detector.py
```

The preview is hidden by default. Press **F8** to show or hide it. Closing the preview window hides the preview but does not necessarily end monitoring. Use **Ctrl+C** in the terminal to stop a manually started detector.

### Register trusted faces

In **Trusted Faces → Register trusted person**, register only people who agree to have their facial features stored. The registration workflow collects multiple samples and saves embeddings locally in `trusted_faces/registry.json`. Stop monitoring before registration or recognition testing so the webcam is free.

Use **Trusted Faces → Test face recognition** to verify recognition. Restart the detector after adding or removing a person. A trusted face does not suppress alerts for another unknown face present in the same frame.

### Automatic startup

Use **Startup Management → Install automatic startup** from the control panel. CameraDetector uses a Windows Task Scheduler logon task named `CameraDetector`, launched by the Python virtual environment's `pythonw.exe`. Startup is optional and requires explicit user action. The current task setup expects `.venv` in the project directory and may need adjustment for particular Windows account configurations.

The detector is designed to release the webcam when Windows is locked; it is not a pre-login monitoring service.

## Detection sensitivity and configuration

Detection and recognition are **separate** processes:

- **YuNet `yunet_score_threshold`** determines how confidently a face must be detected. **Lower values are more sensitive** and may produce more false detections. The controller accepts values from `0.50` to `0.99`.
- **SFace `MATCH_THRESHOLD`** controls whether a detected face matches a registered person. It is currently defined in `face_recognition_engine.py` (default `0.50` cosine similarity), and **is not changed** by the YuNet sensitivity setting.

| YuNet threshold | Detection behavior (illustrative) |
| --- | --- |
| `0.50` | Very high sensitivity |
| `0.60` | High sensitivity |
| `0.70` | Moderately high sensitivity |
| `0.80` | Balanced |
| `0.90` | Strict (default in the example configuration) |
| `0.95` | Very strict |

Sensitivity descriptions are qualitative rather than guarantees. Test on your own camera and lighting conditions.

An example `config.example.json` includes:

```json
{
  "camera_index": 0,
  "camera_width": 1920,
  "camera_height": 1080,
  "process_width": 960,
  "preview_width": 800,
  "detection_sensitivity": 15,
  "min_face_size": 50,
  "face_confirmation": 0.3,
  "minimum_detection_frames": 3,
  "notification_cooldown": 5.0,
  "notifications_enabled": true,
  "preview_on_startup": false,
  "pause_when_locked": true,
  "reconnect_delay": 3.0,
  "yunet_score_threshold": 0.90
}
```

`camera_index: 0` is only a starting value; the correct index depends on the computer. The older `detection_sensitivity` and `min_face_size` keys are **legacy Haar Cascade settings** retained in configuration for compatibility; they **do not control YuNet**. The CLI instead edits `yunet_score_threshold`.

Your personal `config.json` is excluded by `.gitignore`, so it may contain different values (for example, a YuNet threshold of `0.60`).

## Logs and diagnostics

Local logs live in `logs/`:

- `detector.log` — monitoring activity, detections, camera connections, and session events.
- `errors.log` — exceptions and errors.

Each active log can grow to around **2 MB**, with up to **three rotated backups**. This is size-based retention, not a time-based deletion policy.

## Troubleshooting

**`ModuleNotFoundError: No module named 'cv2'`:** Activate the project's `.venv` before running Python, or run `.venv\Scripts\python.exe detector.py` from the project directory.

**Webcam does not start or is already in use:** Stop the scheduled monitoring task and other camera apps. Inspect `logs/detector.log` and `logs/errors.log`, then restart monitoring.

**Wrong webcam is selected:** Stop monitoring, rescan under **Camera Settings**, select the correct index, and restart.

**Model initialization fails:** Run `python download_models.py` to verify/download the YuNet and SFace `.onnx` files. YuNet must be loaded by `cv2.FaceDetectorYN`, and SFace by `cv2.FaceRecognizerSF`.

**Face recognition fails or repeated exceptions appear:** Review `logs/errors.log`; ensure the recognition engine initializes both models. Use **Trusted Faces → Test face recognition** with monitoring stopped.

**An unknown face is matched as trusted:** SFace similarity scores are not probabilities of identity. Test under varied lighting and with multiple people. Do not treat a match as proof of identity.

**Notifications do not appear:** Check Windows Notifications/Do Not Disturb and the CLI's notification setting.

## Privacy and limitations

- **Facial embeddings are biometric data**, even if stored as numbers rather than photos. Keep `trusted_faces/registry.json` private; do not share it or commit it.
- Face processing and registry storage are intended to remain on the local computer; the application does not intentionally upload webcam frames or face embeddings to a cloud service.
- Stored embeddings are **not encrypted at rest** by the application. Protect your Windows account and files.
- `.gitignore` excludes local configuration, biometric registry, logs, virtual environments, and downloaded `.onnx` models; it cannot retroactively remove previously committed information.
- Respect consent, privacy, and relevant rules whenever a webcam may record or monitor other people.
- The unknown-face confirmation mechanism is based on consecutive detections rather than persistent multi-frame identity tracking.
- DirectShow camera indices can change; a clean installation on another Windows 11 machine has not yet been verified.

## Project layout

```text
CameraDetector/
├── README.md
├── .gitignore
├── requirements.txt
├── config.example.json
├── config_manager.py
├── control.py
├── detector.py
├── face_recognition_engine.py
├── face_registration.py
├── trusted_faces.py
├── test_recognition.py
├── session_monitor.py
├── startup_manager.py
├── logger_manager.py
├── log_viewer.py
├── download_models.py
├── models/              # models downloaded locally
├── trusted_faces/       # private local biometric data
└── logs/                # local rotating logs
```

## Third-party models and licensing

YuNet and SFace models come from OpenCV Zoo and retain their respective third-party terms. Review the model notices/licenses if redistributing or using them commercially. The project currently provides a downloader rather than bundling `.onnx` files.

**No software license has been selected for the original CameraDetector code.** The repository is publicly viewable, but public availability alone does not grant permission to reuse or redistribute that code. Standard copyright restrictions apply unless a license is added later.

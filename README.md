# CameraDetector

**CameraDetector** is a Windows webcam-monitoring application written in Python. It detects faces, compares them with locally registered trusted faces, and requests a Windows desktop notification when an **unrecognized face** is confirmed.

It includes a command-line control panel for managing cameras, detection settings, trusted people, notifications, Windows startup, and diagnostic logs.

> **Status:** Early release / personal project. Facial recognition is probabilistic and may produce false matches or missed detections. Do not use this as your only security or access-control system.

## Features

- **Face detection and recognition:** OpenCV YuNet and SFace models.
- **Trusted faces:** Enroll multiple consenting people; suppress alerts when only trusted faces are recognized.
- **Unknown-person alerts:** Request Windows toast notifications for confirmed unrecognized faces, including when trusted and unknown people appear together.
- **Confirmation filter:** Require a configurable detection duration and number of consecutive frames.
- **Webcam selection:** Scan DirectShow cameras and choose an available device in the CLI.
- **Background monitoring:** Hide the preview, or toggle it with **F8** while the detector is running in your signed-in Windows session.
- **Windows session integration:** Release the webcam when Windows locks and reconnect after unlocking.
- **Optional automatic startup:** Manage a Windows Task Scheduler task through the CLI.
- **Rotating logs:** Keep bounded local event and error logs; oldest backups are overwritten.

## Requirements

- **Windows 11** (developed and tested on Windows 11; other versions are not verified).
- **Python 3.13**, preferably 64-bit.
- A Windows-compatible webcam and access to it under **Settings → Privacy & security → Camera**.
- Internet access once to install Python packages and download face-recognition models.

This application uses Windows-specific packages and APIs (`pywin32`, `winotify`, DirectShow), so it is **not currently cross-platform**.

## Installation

### 1. Get the project

Clone the repository (replace the placeholder URL with this project's actual GitHub URL once published):

```powershell
git clone https://github.com/YOUR_USERNAME/CameraDetector.git
cd CameraDetector
```

Or download and extract the repository ZIP, then open a terminal in the extracted folder.

### 2. Create the virtual environment

In **PowerShell**:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

In **Command Prompt (CMD)**:

```cmd
py -3.13 -m venv .venv
.venv\Scripts\activate
```

If PowerShell blocks activation, use CMD rather than broadly changing your script execution policy.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Download the recognition models

```powershell
python download_models.py
```

This downloads the OpenCV Zoo **YuNet** face detector and **SFace** recognizer into `models/` and verifies their SHA-256 checksums. Model files are not committed to this repository.

### 5. Configure your camera

Start the control panel:

```powershell
python control.py
```

On first use, `config_manager.py` creates a local `config.json` from `config.example.json` if needed. Open **Camera Settings**, stop monitoring if it is running, scan available cameras, and choose the desired camera. Indices and friendly device names can vary by computer; verify the selection using the preview.

## Using CameraDetector

### CLI control panel

```powershell
python control.py
```

The main menu is organized into these categories:

| Menu | What it manages |
| --- | --- |
| Monitoring Control | Scheduled-task status; start, stop, restart |
| Detection Settings | Face confirmation duration, minimum detection frames; legacy detection options |
| Trusted Faces | Register, list, remove, test recognition |
| Camera Settings | Scan, select, inspect camera index |
| Notification Settings | Enable/disable alerts; edit cooldown |
| Startup Management | Install, remove, inspect Task Scheduler startup |
| Logs & Diagnostics | View activity, errors, camera/session events, log sizes |

Changes to `config.json` take effect **after restarting the detector**. Closing the CLI itself does not stop a detector launched by Task Scheduler.

### Start manually

```powershell
python detector.py
```

The preview is hidden by default. Press **F8** to show or hide it. Closing the preview window does **not** stop monitoring. When started manually with `python.exe`, use **Ctrl+C** in the terminal to stop the process.

### Trusted faces

In `control.py`, go to **Trusted Faces → Register trusted person**. Stop the monitoring task first so the registration tool can access the camera. Enroll only people who consent to having their facial features stored. The enrollment tool gathers multiple face samples and saves facial embeddings locally in `trusted_faces/registry.json`.

Use **Trusted Faces → Test face recognition** to verify matches. Registered people should appear as trusted; unrecognized people should be marked unknown. **Restart monitoring after adding or removing a trusted person** so the running detector reloads the registry.

**Important:** A trusted match suppresses alerts only for that face. If an unknown face is also detected, the application can still alert. Matching can be wrong under different lighting or angles, so test it thoroughly before relying on it.

### Automatic startup

From the CLI, choose **Startup Management → Install automatic startup**. The application uses a Windows Task Scheduler logon task and runs through `.venv\Scripts\pythonw.exe` without a visible console. Startup is optional and should be explicitly enabled by the user.

The current installer expects a `.venv` inside the project directory and may need adjustments for unusual Windows account configurations or permissions. The default task name is `CameraDetector`. Use the CLI to check or remove its startup registration.

The detector is designed to monitor only while the signed-in Windows session is **unlocked**; it releases the camera while Windows is locked. It does not run as a pre-login surveillance service.

## Configuration

`config.example.json` is a distributable template. `config.json` is the user's local configuration and is ignored by Git.

Typical settings include:

```json
{
  "camera_index": 0,
  "camera_width": 1920,
  "camera_height": 1080,
  "process_width": 960,
  "preview_width": 800,
  "detection_sensitivity": 5,
  "min_face_size": 60,
  "face_confirmation": 0.5,
  "notification_cooldown": 5.0,
  "minimum_detection_frames": 5,
  "notifications_enabled": true,
  "preview_on_startup": false,
  "pause_when_locked": true,
  "reconnect_delay": 3.0
}
```

**Note:** The current primary recognition pipeline uses **YuNet + SFace**. The `detection_sensitivity` and `min_face_size` values originated with the older Haar Cascade detector and **do not currently tune YuNet**. They are retained for compatibility; the CLI should eventually hide or repurpose these controls. This example uses `camera_index: 0` as a starting point, not a guarantee that index 0 is the desired webcam.

The current SFace recognition implementation uses a fixed cosine-similarity threshold defined in `face_recognition_engine.py`. It requires testing with different trusted and unknown people; similarity scores are not identity probabilities.

## Logs and diagnostics

Logs are stored locally under `logs/`:

- `detector.log`: application activity, camera connections, unknown-face confirmations, session changes.
- `errors.log`: errors and exceptions.

Logs are size-rotated: each file may grow to approximately **2 MB**, with up to **three backups**. The oldest backups are overwritten automatically. This is **size-based retention**, not deletion after a number of days. The Logs & Diagnostics menu can show recent events; some views currently show only the active log files, not rotated backups.

## Privacy and security

- Facial **embeddings are biometric data**. Treat `trusted_faces/registry.json` as sensitive; do not commit or share it.
- The registration tool saves feature vectors, not a permanent gallery of enrollment photos. Feature vectors are **not anonymous**.
- Recognition processing and the registry are local; the program is not designed to upload webcam frames or face embeddings to a cloud service.
- This project does not provide encryption at rest for the trusted-face registry. Protect your Windows account and local files.
- `config.json`, `trusted_faces/`, `logs/`, virtual environments, and downloaded `.onnx` models are excluded from Git through `.gitignore`.
- `.gitignore` does **not** remove data that has already been committed. Check `git status` and your commit history before making the repository public.
- Respect the privacy and consent of people who may appear on camera, and comply with applicable rules for workplace or shared-space monitoring.

## Troubleshooting

**The process runs, but the camera light is off.** Check the CLI's task status, inspect `logs/detector.log` and `logs/errors.log`, and try restarting monitoring. A delayed logon task may help with device initialization. Confirm another app isn't using the camera.

**The wrong camera opens.** Stop monitoring, scan under **Camera Settings**, select the correct index, and restart monitoring.

**Notifications don't appear.** Verify Windows Notifications and Do Not Disturb settings, then confirm notifications are enabled in the CLI.

**Recognition doesn't work.** Run `python download_models.py` to check model files; stop monitoring and use **Trusted Faces → Test face recognition**. Re-enroll consenting trusted people under varied lighting if necessary.

**An unknown person is labeled trusted.** Recognition is probabilistic. Do not treat the result as proof of identity. Adjust and evaluate the recognition threshold only after testing against multiple different people.

## Project files

```text
CameraDetector/
├── detector.py
├── control.py
├── config_manager.py
├── config.example.json
├── face_recognition_engine.py
├── face_registration.py
├── trusted_faces.py
├── test_recognition.py
├── session_monitor.py
├── startup_manager.py
├── logger_manager.py
├── log_viewer.py
├── download_models.py
├── requirements.txt
├── .gitignore
├── models/                 # downloaded locally
├── trusted_faces/          # private biometric data; ignored
└── logs/                   # local rotating logs; ignored
```

## Technologies

Python · OpenCV · OpenCV Zoo (YuNet / SFace) · NumPy · PyGrabber · pywin32 · winotify · Windows Task Scheduler

## Limitations and next steps

- Face recognition can falsely accept or reject identities; it is not equivalent to secure biometric authentication.
- Unknown-face confirmation currently counts consecutive frames containing an unknown candidate; it does **not** maintain persistent identity tracking across frames.
- Camera indexing depends on DirectShow enumeration and may change after devices are connected or removed.
- CLI configuration changes require restarting the monitoring process.
- Some older Haar Cascade settings remain visible but unused by the YuNet detector.
- Full clean-install testing on another Windows 11 computer is still recommended before declaring a stable release.

## Third-party models

YuNet and SFace models are downloaded from the **OpenCV Zoo** project. Review their accompanying model licenses and notices before redistribution or commercial use. This repository distributes a downloader rather than checking the `.onnx` files into Git.

## License

**License not yet selected.** Add an appropriate `LICENSE` file before declaring this an open-source release. Until then, standard copyright restrictions apply to the original project code.

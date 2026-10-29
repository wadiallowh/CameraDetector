
import ctypes
import threading

import win32api
import win32gui
import win32ts


# ==========================================
# WINDOWS SESSION EVENT CONSTANTS
# ==========================================

WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8

DESKTOP_SWITCHDESKTOP = 0x0100


# ==========================================
# SESSION MONITOR
# ==========================================

class SessionMonitor:

    def __init__(self):
        # Start in the safe state: monitoring paused
        self._locked = threading.Event()
        self._locked.set()

        self._ready = threading.Event()
        self._stop = threading.Event()

        self._thread = None
        self._error = None

    @property
    def is_locked(self):
        return self._locked.is_set()

    # ======================================
    # CHECK CURRENT WINDOWS SESSION
    # ======================================

    def _current_lock_state(self):

        user32 = ctypes.WinDLL(
            "user32",
            use_last_error=True
        )

        user32.OpenInputDesktop.restype = ctypes.c_void_p
        user32.OpenInputDesktop.argtypes = [
            ctypes.c_uint,
            ctypes.c_bool,
            ctypes.c_uint
        ]

        user32.CloseDesktop.argtypes = [
            ctypes.c_void_p
        ]

        desktop = user32.OpenInputDesktop(
            0,
            False,
            DESKTOP_SWITCHDESKTOP
        )

        if not desktop:
            return True

        try:
            # Check whether the input desktop
            # can be switched to.
            user32.SwitchDesktop.restype = ctypes.c_bool
            user32.SwitchDesktop.argtypes = [
                ctypes.c_void_p
            ]

            return not bool(
                user32.SwitchDesktop(desktop)
            )

        finally:
            user32.CloseDesktop(desktop)

    # ======================================
    # HANDLE LOCK / UNLOCK EVENTS
    # ======================================

    def _on_session_change(
        self,
        hwnd,
        msg,
        event,
        session_id
    ):

        if event == WTS_SESSION_LOCK:
            self._locked.set()
            print(
                "[SESSION] Windows locked.",
                flush=True
            )

        elif event == WTS_SESSION_UNLOCK:
            self._locked.clear()
            print(
                "[SESSION] Windows unlocked.",
                flush=True
            )

        return 0

    # ======================================
    # BACKGROUND EVENT LISTENER
    # ======================================

    def _run(self):

        hwnd = None
        registered = False

        try:
            instance = win32api.GetModuleHandle(None)

            window_class = win32gui.WNDCLASS()

            window_class.hInstance = instance
            window_class.lpszClassName = (
                "CameraDetectorSessionMonitor_"
                + str(id(self))
            )

            window_class.lpfnWndProc = {
                WM_WTSSESSION_CHANGE:
                    self._on_session_change
            }

            class_atom = win32gui.RegisterClass(
                window_class
            )

            hwnd = win32gui.CreateWindow(
                class_atom,
                "CameraDetector Session Listener",
                0,
                0, 0, 0, 0,
                0,
                0,
                instance,
                None
            )

            win32ts.WTSRegisterSessionNotification(
                hwnd,
                win32ts.NOTIFY_FOR_THIS_SESSION
            )

            registered = True

            # Detect initial lock state
            if self._current_lock_state():
                self._locked.set()
            else:
                self._locked.clear()

            self._ready.set()

            # Process Windows session events
            while not self._stop.is_set():

                win32gui.PumpWaitingMessages()

                self._stop.wait(0.1)

        except Exception as error:

            self._error = error
            self._locked.set()
            self._ready.set()

            print(
                f"[SESSION ERROR] {error}",
                flush=True
            )

        finally:

            if registered and hwnd is not None:
                win32ts.WTSUnRegisterSessionNotification(
                    hwnd
                )

            if hwnd is not None:
                win32gui.DestroyWindow(hwnd)

    # ======================================
    # START SESSION MONITOR
    # ======================================

    def start(self):

        if self._thread is not None:
            if self._thread.is_alive():
                return

            raise RuntimeError(
                "Session monitor cannot be restarted."
            )

        self._thread = threading.Thread(
            target=self._run,
            name="CameraDetectorSessionMonitor",
            daemon=True
        )

        self._thread.start()

        if not self._ready.wait(timeout=5):
            self._locked.set()
            raise RuntimeError(
                "Session monitor initialization timed out."
            )

        if self._error is not None:
            raise RuntimeError(
                f"Session monitor failed: {self._error}"
            )

        if not self._thread.is_alive():
            raise RuntimeError(
                "Session monitor stopped unexpectedly."
            )

    # ======================================
    # STOP SESSION MONITOR
    # ======================================

    def stop(self):

        self._stop.set()
        self._locked.set()

        if self._thread is not None:
            self._thread.join(timeout=2)

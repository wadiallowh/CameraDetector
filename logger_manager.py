
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


# ==========================================
# LOGGING CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)

MAX_LOG_SIZE = 2 * 1024 * 1024
BACKUP_COUNT = 3

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | "
    "%(name)s | %(message)s"
)


# ==========================================
# LOGGER FACTORY
# ==========================================

def get_logger(name="CameraDetector"):

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ======================================
    # MAIN APPLICATION LOG
    # ======================================

    main_handler = RotatingFileHandler(
        LOG_DIR / "detector.log",
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )

    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(formatter)

    # ======================================
    # ERROR LOG
    # ======================================

    error_handler = RotatingFileHandler(
        LOG_DIR / "errors.log",
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )

    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    logger.addHandler(main_handler)
    logger.addHandler(error_handler)

    return logger


import json
import shutil
from pathlib import Path


# ==========================================
# CONFIGURATION FILE PATHS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

CONFIG_FILE = BASE_DIR / "config.json"
EXAMPLE_CONFIG_FILE = BASE_DIR / "config.example.json"


# ==========================================
# INITIALIZE CONFIGURATION
# ==========================================

def initialize_config():
    """
    Create config.json from config.example.json
    only if the configuration does not exist.
    """

    if CONFIG_FILE.exists():
        return

    if not EXAMPLE_CONFIG_FILE.exists():
        raise FileNotFoundError(
            "Configuration template not found: "
            "config.example.json"
        )

    shutil.copyfile(
        EXAMPLE_CONFIG_FILE,
        CONFIG_FILE
    )

    print(
        "[CONFIG] First-time configuration created "
        "from config.example.json."
    )


# ==========================================
# LOAD CONFIGURATION
# ==========================================

def load_config():
    """
    Load application settings.

    Automatically initialize the configuration
    on first launch.
    """

    initialize_config()

    with open(
        CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        config = json.load(file)

    if not isinstance(config, dict):
        raise ValueError(
            "Configuration must be a JSON object."
        )

    return config


# ==========================================
# SAVE CONFIGURATION
# ==========================================

def save_config(config):
    """
    Save settings using a temporary file
    to avoid partially written configuration.
    """

    if not isinstance(config, dict):
        raise TypeError(
            "Configuration must be a dictionary."
        )

    initialize_config()

    temporary_file = CONFIG_FILE.with_suffix(
        ".json.tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            config,
            file,
            indent=4
        )

        file.write("\n")

    temporary_file.replace(CONFIG_FILE)


# ==========================================
# UPDATE INDIVIDUAL SETTING
# ==========================================

def update_setting(key, value):
    """
    Update an existing configuration setting.
    """

    config = load_config()

    if key not in config:
        raise KeyError(
            f"Unknown configuration setting: {key}"
        )

    config[key] = value

    save_config(config)


# ==========================================
# CHECK CONFIGURATION STATUS
# ==========================================

def config_status():
    """
    Display configuration file information.
    """

    print("\n=== CAMERA DETECTOR CONFIGURATION ===")

    if CONFIG_FILE.exists():
        print("Configuration: Installed")
        print(f"Location: {CONFIG_FILE}")

    else:
        print("Configuration: Not initialized")

    if EXAMPLE_CONFIG_FILE.exists():
        print("Template: Available")
    else:
        print("Template: Missing")


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":
    config_status()

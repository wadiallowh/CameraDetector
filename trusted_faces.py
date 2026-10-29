
import json
from pathlib import Path

import numpy as np


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "trusted_faces"
REGISTRY_FILE = DATA_DIR / "registry.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_registry():
    """Load registered trusted identities."""
    if not REGISTRY_FILE.exists():
        return {}

    with open(REGISTRY_FILE, "r", encoding="utf-8-sig") as file:
        return json.load(file)


def save_registry(registry):
    """Save registered trusted identities."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temporary = REGISTRY_FILE.with_suffix(".json.tmp")

    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(registry, file, indent=4)

    temporary.replace(REGISTRY_FILE)


def register_person(name, embeddings):
    """Store embeddings associated with a trusted person."""
    name = name.strip()

    if not name:
        raise ValueError("Person name cannot be empty.")

    if not embeddings:
        raise ValueError("At least one embedding is required.")

    registry = load_registry()

    if name in registry:
        raise ValueError(
            f"{name} is already registered."
        )

    registry[name] = [
        np.asarray(embedding, dtype=np.float32)
        .flatten()
        .tolist()
        for embedding in embeddings
    ]

    save_registry(registry)


def list_people():
    """Return names of registered trusted people."""
    return list(load_registry().keys())


def remove_person(name):
    """Delete a registered person's embeddings."""
    registry = load_registry()

    if name not in registry:
        return False

    del registry[name]
    save_registry(registry)

    return True

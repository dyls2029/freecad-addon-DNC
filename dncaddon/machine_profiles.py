import json
import os
import FreeCAD

PROFILE_DIR = os.path.join(FreeCAD.getUserAppDataDir(), "DNCAddon", "profiles")


def ensure_profile_dir():
    os.makedirs(PROFILE_DIR, exist_ok=True)


def list_profiles():
    ensure_profile_dir()
    return [name[:-5] for name in sorted(os.listdir(PROFILE_DIR)) if name.endswith('.json')]


def save_profile(name, settings):
    ensure_profile_dir()
    with open(os.path.join(PROFILE_DIR, f"{name}.json"), "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)


def load_profile(name):
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def delete_profile(name):
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)

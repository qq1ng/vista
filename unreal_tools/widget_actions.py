# Functions for the Editor Utility Widget buttons.
# Each button runs one line of Python through the "Execute Python Command" node, for example:
#   from unreal_tools import widget_actions; widget_actions.build(r"C:/vista_out/manifest.json")

import importlib
import os
import unreal
from core import cuts
from core import manifest
from core import validate
from unreal_tools import build_sequence


# reloads the vista modules, so a code change takes effect without an editor restart
def reload_vista():
    importlib.reload(manifest)
    importlib.reload(cuts)
    importlib.reload(validate)
    importlib.reload(build_sequence)


# cleans a path pasted into a text box: spaces, quotes and backslashes
def clean_path(path):
    path = path.strip()
    path = path.strip('"')
    path = path.strip("'")
    return path.replace("\\", "/")


# reads the manifest, or logs why it cannot, returns None on failure
def load_manifest(manifest_path):
    if not os.path.isfile(manifest_path):
        unreal.log_error(f"Vista: no file at {manifest_path}")
        return None
    try:
        return manifest.read_manifest(manifest_path)
    except ValueError as error:
        unreal.log_error(f"Vista: {error}")
        return None


# checks the manifest and logs every issue, builds nothing
def check(manifest_path):
    reload_vista()
    manifest_path = clean_path(manifest_path)
    manifest_data = load_manifest(manifest_path)
    if manifest_data is None:
        return False

    issues = validate.validate_manifest(manifest_data)
    issues.extend(validate.check_filmback_presets(manifest_data, build_sequence.get_filmback_presets()))
    build_sequence.log_issues(issues)
    if validate.has_errors(issues):
        unreal.log_error("Vista: check failed.")
        return False
    unreal.log("Vista: check passed.")
    return True


# builds the Level Sequence from the manifest
def build(manifest_path):
    reload_vista()
    manifest_path = clean_path(manifest_path)
    if load_manifest(manifest_path) is None:
        return None
    return build_sequence.build_from_manifest(manifest_path)

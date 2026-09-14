# Functions for the Vista panel and the Vista menu.
# Each button or menu entry runs one line of Python, for example:
#   from unreal_tools import widget_actions; widget_actions.build(r"C:/vista_out/manifest.json", "true")
# An empty path means the manifest Maya wrote last.

import importlib
import os
import unreal
from core import cuts
from core import last_export
from core import manifest
from core import validate
from unreal_tools import build_sequence


PANEL_ASSET = "/Game/Vista/EUW_Vista"

# widget names inside the panel, each with Is Variable ticked in the Designer
PANEL_PATH_BOX = "ManifestPathBox"
PANEL_LOCK_BOX = "LockViewportBox"
PANEL_STATUS_TEXT = "StatusText"


# reloads the vista modules, so a code change takes effect without an editor restart
def reload_vista():
    importlib.reload(manifest)
    importlib.reload(cuts)
    importlib.reload(validate)
    importlib.reload(last_export)
    importlib.reload(build_sequence)


# cleans a path pasted into a text box: spaces, quotes and backslashes
def clean_path(path):
    path = path.strip()
    path = path.strip('"')
    path = path.strip("'")
    return path.replace("\\", "/")


# a Blueprint tick arrives as the text "true" or "false", Python code passes True or False
def to_bool(value):
    return str(value).strip().lower() == "true"


# the path to use: the given one, or the last Maya export when the box is empty
# returns None, and logs why, when there is no path to use
def pick_manifest_path(manifest_path):
    manifest_path = clean_path(manifest_path)
    if manifest_path != "":
        return manifest_path
    last_path = last_export.read_last_export()
    if last_path is None:
        unreal.log_error("Vista: the path is empty, and Maya has no last export yet. Export from Maya first.")
        return None
    unreal.log(f"Vista: using the last export, {last_path}")
    return last_path


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


# every issue a build checks, nothing logged
def collect_issues(manifest_data, manifest_path):
    issues = validate.validate_manifest(manifest_data)
    issues.extend(validate.check_files_exist(manifest_data, manifest_path))
    issues.extend(validate.check_filmback_presets(manifest_data, build_sequence.get_filmback_presets()))
    return issues


# checks the manifest and logs every issue, builds nothing
# returns one status line for the panel
def check(manifest_path):
    reload_vista()
    manifest_path = pick_manifest_path(manifest_path)
    if manifest_path is None:
        return "No manifest. Export from Maya first."
    manifest_data = load_manifest(manifest_path)
    if manifest_data is None:
        return "Cannot read the manifest. See the Output Log."

    issues = collect_issues(manifest_data, manifest_path)
    build_sequence.log_issues(issues)
    summary = validate.summarize_issues(issues)
    if validate.has_errors(issues):
        unreal.log_error(f"Vista: check failed, {summary}.")
        return f"Check failed: {summary}. See the Output Log."
    unreal.log(f"Vista: check passed, {summary}.")
    return f"Check passed: {summary}."


# builds the Level Sequence from the manifest, returns one status line for the panel
# lock_viewport locks the viewport to the camera cuts after the build
def build(manifest_path, lock_viewport=True):
    reload_vista()
    manifest_path = pick_manifest_path(manifest_path)
    if manifest_path is None:
        return "No manifest. Export from Maya first."
    manifest_data = load_manifest(manifest_path)
    if manifest_data is None:
        return "Cannot read the manifest. See the Output Log."

    summary = validate.summarize_issues(collect_issues(manifest_data, manifest_path))
    sequence = build_sequence.build_from_manifest(manifest_path, to_bool(lock_viewport))
    if sequence is None:
        return f"Build failed: {summary}. See the Output Log."
    shot_count = len(manifest_data["shots"])
    character_count = len(manifest_data["characters"])
    return (
        f"Built {sequence.get_name()}: {shot_count} {validate.plural(shot_count, 'shot')}, "
        f"{character_count} {validate.plural(character_count, 'character')}, {summary}."
    )


# the manifest path Maya wrote last, or "" when there is none, for the Last Export button
def get_last_export_path():
    last_path = last_export.read_last_export()
    if last_path is None:
        return ""
    return last_path


# opens a file dialog for a manifest, returns the chosen path, or "" when the artist cancels
# tkinter ships with Unreal's Python, and only this button needs it, so the import sits here
def browse():
    import tkinter
    from tkinter import filedialog

    start_folder = ""
    last_path = last_export.read_last_export()
    if last_path is not None:
        start_folder = os.path.dirname(last_path)

    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        parent=root,
        title="Pick a vista manifest",
        initialdir=start_folder,
        filetypes=[("vista manifest", "*.json"), ("All files", "*.*")],
    )
    root.destroy()
    if not path:
        return ""
    return clean_path(path)


# opens the Vista panel, the Editor Utility Widget, as an editor tab
def open_panel():
    panel = unreal.load_asset(PANEL_ASSET)
    if panel is None:
        unreal.log_error(
            f"Vista: no panel at {PANEL_ASSET}. "
            f"Copy unreal_tools/content/EUW_Vista.uasset into your project's Content/Vista folder."
        )
        return None
    return unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).spawn_and_register_tab(panel)


# ---------------------------------------------------------------------------------------------
# The panel buttons. Each button runs one line, for example:
#   from unreal_tools import widget_actions; widget_actions.panel_build()
# Python reads the path box and the tick from the panel, and writes the status line back.
# ---------------------------------------------------------------------------------------------


# the open Vista panel, or None when it is not open
def find_panel():
    blueprint = unreal.load_asset(PANEL_ASSET)
    if blueprint is None:
        return None
    return unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).find_utility_widget_from_blueprint(blueprint)


# one named widget inside the panel, or None when the panel has no widget of that name
# Python sees only widgets with Is Variable ticked, so a missing tick also gives None
def get_panel_widget(panel, name):
    if panel is None:
        return None
    try:
        return panel.get_editor_property(name)
    except Exception:
        return None


# the text in the panel's path box
def read_panel_path(panel):
    box = get_panel_widget(panel, PANEL_PATH_BOX)
    if box is None:
        return ""
    return str(box.get_text())


# puts a path into the panel's path box
def write_panel_path(panel, manifest_path):
    box = get_panel_widget(panel, PANEL_PATH_BOX)
    if box is not None:
        box.set_text(manifest_path)


# the panel's "lock viewport" tick, on when the panel has no tick
def read_panel_lock(panel):
    tick = get_panel_widget(panel, PANEL_LOCK_BOX)
    if tick is None:
        return True
    return tick.is_checked()


# writes one line into the panel's status text
def show_status(panel, status):
    status_text = get_panel_widget(panel, PANEL_STATUS_TEXT)
    if status_text is not None:
        status_text.set_text(status)


# Browse button: a file dialog, the chosen path goes into the path box
def panel_browse():
    panel = find_panel()
    manifest_path = browse()
    if manifest_path != "":
        write_panel_path(panel, manifest_path)
        show_status(panel, "Manifest picked. Press Check or Build.")


# Last Export button: the manifest Maya wrote last goes into the path box
def panel_last_export():
    panel = find_panel()
    manifest_path = get_last_export_path()
    if manifest_path == "":
        show_status(panel, "Maya has no last export yet. Export from Maya first.")
        return
    write_panel_path(panel, manifest_path)
    show_status(panel, "Last export picked. Press Check or Build.")


# Check button
def panel_check():
    panel = find_panel()
    show_status(panel, check(read_panel_path(panel)))


# Build button
def panel_build():
    panel = find_panel()
    show_status(panel, build(read_panel_path(panel), read_panel_lock(panel)))

import os
from core import cuts
from core import manifest


ERROR = "error"
WARNING = "warning"
INFO = "info"


# one issue is one message for the artist, with level of severity
def make_issue(level, message):
    return {"level": level, "message": message}


# true when at least one issue stops the export
def has_errors(issues):
    for issue in issues:
        if issue["level"] == ERROR:
            return True
    return False


# one line of text for a log or a print
def format_issue(issue):
    return f"[{issue['level'].upper()}] {issue['message']}"


# the word, with an "s" when the count is not one
def plural(count, word):
    if count == 1:
        return word
    return word + "s"


# counts errors and warnings for a one-line status, for example "0 errors, 1 warning"
def summarize_issues(issues):
    errors = 0
    warnings = 0
    for issue in issues:
        if issue["level"] == ERROR:
            errors = errors + 1
        elif issue["level"] == WARNING:
            warnings = warnings + 1
    return f"{errors} {plural(errors, 'error')}, {warnings} {plural(warnings, 'warning')}"


# rule: the manifest needs at least one shot
def check_has_shots(manifest_data):
    issues = []
    if len(manifest_data["shots"]) == 0:
        issues.append(make_issue(
            ERROR,
            "The scene has no keyed camera. Key at least one camera, then export again.",
        ))
    return issues


# rule: two items must not export to the same FBX file name
def check_unique_names(manifest_data):
    issues = []
    seen = {}
    items = manifest_data["shots"] + manifest_data["characters"]
    for item in items:
        file_name = manifest.safe_name(item["name"])
        if file_name in seen:
            issues.append(make_issue(
                ERROR,
                f"'{item['name']}' and '{seen[file_name]}' both export to '{file_name}.fbx'. "
                f"Rename one of them in Maya.",
            ))
        else:
            seen[file_name] = item["name"]
    return issues


# rule: every shot must sit inside the scene range
def check_shot_ranges(manifest_data):
    issues = []
    scene = manifest_data["scene"]
    scene_start = scene["frame_start"]
    scene_end = scene["frame_end"]

    for shot in manifest_data["shots"]:
        name = shot["name"]
        start = shot["frame_start"]
        end = shot["frame_end"]

        if start > scene_end or end < scene_start:
            issues.append(make_issue(
                WARNING,
                f"Shot '{name}' has keys from frame {start} to {end}. The scene range is "
                f"{scene_start} to {scene_end}. The sequence does not show this shot. "
                f"Move the keys or change the playback range.",
            ))
        elif start < scene_start or end > scene_end:
            issues.append(make_issue(
                WARNING,
                f"Shot '{name}' has keys from frame {start} to {end}. The scene range is "
                f"{scene_start} to {scene_end}. The FBX holds only the frames inside the scene range.",
            ))
    return issues


# rule: a shot that starts before the previous shot ends loses frames
def check_overlaps(manifest_data):
    issues = []
    shots = sorted(manifest_data["shots"], key=cuts.shot_sort_key)

    for index in range(1, len(shots)):
        previous = shots[index - 1]
        shot = shots[index]

        if shot["frame_start"] == previous["frame_start"]:
            issues.append(make_issue(
                WARNING,
                f"Shots '{previous['name']}' and '{shot['name']}' both start at frame "
                f"{shot['frame_start']}. Only '{shot['name']}' appears in the cut list.",
            ))
        elif shot["frame_start"] <= previous["frame_end"]:
            issues.append(make_issue(
                WARNING,
                f"Shot '{shot['name']}' starts at frame {shot['frame_start']}, before shot "
                f"'{previous['name']}' ends at frame {previous['frame_end']}. The cut happens at "
                f"frame {shot['frame_start']}. The last frames of '{previous['name']}' do not show.",
            ))
    return issues


# rule: every FBX file the manifest names must exist
# needs the manifest path, because the FBX paths are relative to it
def check_files_exist(manifest_data, manifest_path):
    issues = []
    items = manifest_data["shots"] + manifest_data["characters"]
    for item in items:
        fbx_path = manifest.resolve_path(item["fbx_path"], manifest_path)
        if not os.path.isfile(fbx_path):
            issues.append(make_issue(
                ERROR,
                f"The FBX file for '{item['name']}' is missing: {fbx_path}. Export again from Maya.",
            ))
    return issues


# runs every rule that needs only the manifest
def validate_manifest(manifest_data):
    issues = []
    issues.extend(check_has_shots(manifest_data))
    issues.extend(check_unique_names(manifest_data))
    issues.extend(check_shot_ranges(manifest_data))
    issues.extend(check_overlaps(manifest_data))
    return issues


# returns the name of the preset that matches the sensor size, or None
# presets is a list of (name, width_mm, height_mm) tuples
def find_filmback_preset(sensor_width_mm, sensor_height_mm, presets, tolerance_mm=0.01):
    for name, width_mm, height_mm in presets:
        width_matches = abs(width_mm - sensor_width_mm) <= tolerance_mm
        height_matches = abs(height_mm - sensor_height_mm) <= tolerance_mm
        if width_matches and height_matches:
            return name
    return None


# rule: say which Unreal filmback preset each shot matches
# Unreal owns the preset list, so the Unreal side passes it in
def check_filmback_presets(manifest_data, presets):
    issues = []
    for shot in manifest_data["shots"]:
        width = shot["sensor_width_mm"]
        height = shot["sensor_height_mm"]
        preset_name = find_filmback_preset(width, height, presets)

        if preset_name is None:
            issues.append(make_issue(
                INFO,
                f"Shot '{shot['name']}' uses a {width} x {height} mm sensor. No Unreal filmback "
                f"preset matches. The tool sets a custom filmback, so the field of view stays correct.",
            ))
        else:
            issues.append(make_issue(
                INFO,
                f"Shot '{shot['name']}' uses a {width} x {height} mm sensor. "
                f"This matches the Unreal preset '{preset_name}'.",
            ))
    return issues

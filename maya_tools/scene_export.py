import os
import maya.mel as mel
import maya.cmds as cmds
from core import manifest
from core import validate
from maya_tools import fbx_utils
from maya_tools import camera_export
from maya_tools import character_export


MANIFEST_NAME = "manifest.json"


# first and last frame of the playback range
def get_scene_range():
    start = cmds.playbackOptions(query=True, minTime=True)
    end = cmds.playbackOptions(query=True, maxTime=True)
    return start, end


# frames per second of the scene, the time unit "film" gives 24.0
def get_scene_fps():
    return mel.eval("currentTimeUnitToFPS()")


# scene file name without folder and extension, "untitled" for a unsaved scene
def get_scene_name():
    file_name = cmds.file(query=True, sceneName=True, shortName=True)
    if not file_name:
        return "untitled"
    return os.path.splitext(file_name)[0]


# builds one shot dict per keyed camera
def collect_shots(camera_transforms, manifest_path):
    shots = []
    issues = []
    output_folder = os.path.dirname(manifest_path)

    for camera in camera_transforms:
        key_range = camera_export.get_key_range(camera)
        if key_range is None:
            issues.append(validate.make_issue(
                validate.WARNING,
                f"Camera '{camera}' has no keys. The tool skips it.",
            ))
            continue

        frame_start, frame_end = key_range
        lens = camera_export.get_lens(camera, frame_start)
        fbx_path = f"{output_folder}/{manifest.safe_name(camera)}.fbx"
        shot = manifest.build_shot(
            camera,
            manifest.make_relative(fbx_path, manifest_path),
            frame_start,
            frame_end,
            lens["focal_length"],
            lens["horizontal_film_aperture"],
            lens["vertical_film_aperture"],
            lens["depth_of_field"],
        )
        shots.append(shot)
    return shots, issues


# builds one character dict per skinned character
# a character FBX is baked over the whole scene range, its range is the scene range
def collect_characters(characters, manifest_path, scene_start, scene_end):
    entries = []
    output_folder = os.path.dirname(manifest_path)
    for character in characters:
        fbx_path = f"{output_folder}/{manifest.safe_name(character['name'])}.fbx"
        entry = manifest.build_character(
            character["name"],
            manifest.make_relative(fbx_path, manifest_path),
            scene_start,
            scene_end,
        )
        entries.append(entry)
    return entries


# keeps only the characters whose root joint is in the given list
def filter_characters(characters, root_joints):
    kept = []
    for character in characters:
        if character["root_joint"] in root_joints:
            kept.append(character)
    return kept


# collects everything, checks it, then exports every FBX and writes the manifest
# returns (manifest_path, issues), manifest_path is None when nothing was written
# camera_transforms and character_roots of None mean "everything in the scene"
def export_scene(output_folder, camera_transforms=None, character_roots=None, dry_run=False):
    fbx_utils.load_fbx_plugin()
    output_folder = output_folder.replace("\\", "/").rstrip("/")
    manifest_path = f"{output_folder}/{MANIFEST_NAME}"

    if camera_transforms is None:
        camera_transforms = camera_export.get_export_cameras()
    characters = character_export.get_characters()
    if character_roots is not None:
        characters = filter_characters(characters, character_roots)

    scene_start, scene_end = get_scene_range()
    scene = manifest.build_scene(get_scene_name(), scene_start, scene_end, get_scene_fps())
    shots, issues = collect_shots(camera_transforms, manifest_path)
    character_entries = collect_characters(characters, manifest_path, scene_start, scene_end)
    manifest_data = manifest.build_manifest(scene, shots, character_entries)
    issues.extend(validate.validate_manifest(manifest_data))

    # check first, then touch the disk: don't write unless free of errors
    if dry_run or validate.has_errors(issues):
        return None, issues

    os.makedirs(output_folder, exist_ok=True)
    for shot in shots:
        fbx_path = manifest.resolve_path(shot["fbx_path"], manifest_path)
        camera_export.export_camera(shot["name"], fbx_path, scene_start, scene_end)

    # collect_characters kept the order of characters, so index i matches in both lists
    for index in range(len(characters)):
        fbx_path = manifest.resolve_path(character_entries[index]["fbx_path"], manifest_path)
        character_export.export_character(characters[index], fbx_path, scene_start, scene_end)

    manifest.write_manifest(manifest_data, manifest_path)
    return manifest_path, issues

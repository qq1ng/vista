import json
import os


MANIFEST_VERSION = 4
INCH_TO_MM = 25.4
DECIMALS = 3


# converts inches to mm, rounded so 1.41732 in gives 36.0 and not 35.999928
def inches_to_mm(inches):
    mm = inches * INCH_TO_MM
    return round(mm, DECIMALS)


# replaces every character that is not safe in a file name or an Unreal asset name
def safe_name(name):
    result = ""
    for character in name:
        if character.isalnum() or character in "_-":
            result = result + character
        else:
            result = result + "_"
    return result


# converts fps to a whole-number fraction, 24.0 gives (24, 1), 23.976 gives (24000, 1001)
def fps_to_fraction(fps):
    whole = round(fps)
    if abs(fps - whole) < 0.01:
        return int(whole), 1
    return int(round(fps * 1001)), 1001


# stores a path relative to the manifest folder, so the folder can move as one unit
def make_relative(path, manifest_path):
    manifest_folder = os.path.dirname(os.path.abspath(manifest_path))
    try:
        relative = os.path.relpath(os.path.abspath(path), manifest_folder)
    except ValueError:
        # relpath fails when the two paths sit on different drives, keep the full path
        return path.replace("\\", "/")
    return relative.replace("\\", "/")


# turns a path from the manifest back into a full path
def resolve_path(path, manifest_path):
    if os.path.isabs(path):
        return path.replace("\\", "/")
    manifest_folder = os.path.dirname(os.path.abspath(manifest_path))
    full_path = os.path.normpath(os.path.join(manifest_folder, path))
    return full_path.replace("\\", "/")


# builds dict holding the scene, its range is the range every FBX is baked over
def build_scene(name, frame_start, frame_end, fps):
    scene_data = {
        "name": name,
        "frame_start": int(round(frame_start)),
        "frame_end": int(round(frame_end)),
        "fps": fps,
    }
    return scene_data


# builds dict holding one shot, takes aperture in inches, stores in mm
# depth_of_field is the depth of field switch on the Maya camera shape
def build_shot(name, fbx_path, frame_start, frame_end, focal_length, horizontal_film_aperture_inches, vertical_film_aperture_inches, depth_of_field=False):
    shot_data = {
        "name": name,
        "fbx_path": fbx_path,
        "frame_start": int(round(frame_start)),
        "frame_end": int(round(frame_end)),
        "focal_length": round(focal_length, DECIMALS),
        "sensor_width_mm": inches_to_mm(horizontal_film_aperture_inches),
        "sensor_height_mm": inches_to_mm(vertical_film_aperture_inches),
        "depth_of_field": bool(depth_of_field),
    }
    return shot_data


# builds dict holding one skinned character, its FBX holds mesh, skeleton and baked animation
def build_character(name, fbx_path, frame_start, frame_end):
    character_data = {
        "name": name,
        "fbx_path": fbx_path,
        "frame_start": int(round(frame_start)),
        "frame_end": int(round(frame_end)),
    }
    return character_data


# builds the whole manifest dict, nothing touches the disk here
def build_manifest(scene, shots, characters):
    manifest_data = {
        "version": MANIFEST_VERSION,
        "scene": scene,
        "shots": shots,
        "characters": characters,
    }
    return manifest_data


# writes the manifest dict to a json file
def write_manifest(manifest_data, manifest_path):
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)


# reads a manifest json file, refuses a file that another version of the tool wrote
def read_manifest(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    version = manifest_data.get("version")
    if version != MANIFEST_VERSION:
        raise ValueError(
            f"Manifest '{manifest_path}' has version {version}. "
            f"This tool reads version {MANIFEST_VERSION}. Export it again from Maya."
        )
    return manifest_data

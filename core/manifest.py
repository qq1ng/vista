import json


INCH_TO_MM = 25.4

def inches_to_mm(inches):
    mm = inches * INCH_TO_MM
    return mm

# builds dict holding one shot, takes aperture in inches, stores in mm
def build_shot(name, fbx_path, frame_start, frame_end, focal_length, aperture_horizontal_inches, aperture_vertical_inches):
    shot_data = {
        "name": name,
        "fbx_path": fbx_path,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "focal_length": focal_length,
        "aperture_horizontal_mm": inches_to_mm(aperture_horizontal_inches),
        "aperture_vertical_mm": inches_to_mm(aperture_vertical_inches),
    }
    return shot_data

# py funct writing json file from build_shot data dict
def write_manifest(shots, manifest_path):
    manifest = {"version": 1, "shots": shots}
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

# py funct reading json file 
def read_manifest(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)
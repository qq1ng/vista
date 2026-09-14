import json
import pytest
from core import manifest


def test_inches_to_mm_rounds_float_noise():
    assert manifest.inches_to_mm(1.41732) == 36.0


def test_build_shot_converts_aperture_to_mm():
    shot = manifest.build_shot("camA", "camA.fbx", 1.0, 60.0, 35.0, 1.41732, 0.94488)
    assert shot["sensor_width_mm"] == 36.0
    assert shot["sensor_height_mm"] == 24.0


def test_build_shot_stores_whole_frames():
    shot = manifest.build_shot("camA", "camA.fbx", 1.0, 60.0, 35.0, 1.41732, 0.94488)
    assert shot["frame_start"] == 1
    assert isinstance(shot["frame_start"], int)


def test_build_shot_rounds_focal_length():
    shot = manifest.build_shot("camA", "camA.fbx", 1, 60, 34.99999999999999, 1.41732, 0.94488)
    assert shot["focal_length"] == 35.0


def test_build_shot_depth_of_field_defaults_to_off():
    shot = manifest.build_shot("camA", "camA.fbx", 1, 60, 35.0, 1.41732, 0.94488)
    assert shot["depth_of_field"] is False


def test_build_shot_stores_maya_depth_of_field_as_bool():
    shot = manifest.build_shot("camA", "camA.fbx", 1, 60, 35.0, 1.41732, 0.94488, 1)
    assert shot["depth_of_field"] is True


def test_safe_name_replaces_path_and_namespace():
    assert manifest.safe_name("grp|mixamorig1:Hips") == "grp_mixamorig1_Hips"


def test_safe_name_keeps_plain_name():
    assert manifest.safe_name("shotCam_A-02") == "shotCam_A-02"


def test_fps_to_fraction_whole_rate():
    assert manifest.fps_to_fraction(24.0) == (24, 1)
    assert manifest.fps_to_fraction(30.0) == (30, 1)


def test_fps_to_fraction_ntsc_rate():
    assert manifest.fps_to_fraction(23.976) == (24000, 1001)
    assert manifest.fps_to_fraction(29.97) == (30000, 1001)


def test_make_relative_same_folder(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    fbx_path = str(tmp_path / "shotCam_A.fbx")
    assert manifest.make_relative(fbx_path, manifest_path) == "shotCam_A.fbx"


def test_make_relative_subfolder_uses_forward_slashes(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    fbx_path = str(tmp_path / "fbx" / "shotCam_A.fbx")
    assert manifest.make_relative(fbx_path, manifest_path) == "fbx/shotCam_A.fbx"


def test_resolve_path_round_trip(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    fbx_path = str(tmp_path / "fbx" / "shotCam_A.fbx").replace("\\", "/")
    relative = manifest.make_relative(fbx_path, manifest_path)
    assert manifest.resolve_path(relative, manifest_path) == fbx_path


def test_resolve_path_keeps_absolute_path(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    absolute = "D:/elsewhere/shotCam_A.fbx"
    assert manifest.resolve_path(absolute, manifest_path) == absolute


def test_write_then_read_round_trip(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    scene = manifest.build_scene("demo", 1, 120, 30.0)
    shot = manifest.build_shot("camA", "camA.fbx", 1, 60, 35.0, 1.41732, 0.94488)
    character = manifest.build_character("Ch36", "Ch36.fbx", 1, 120)
    data = manifest.build_manifest(scene, [shot], [character])

    manifest.write_manifest(data, manifest_path)
    assert manifest.read_manifest(manifest_path) == data


def test_read_refuses_other_version(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"version": 3, "shots": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        manifest.read_manifest(str(manifest_path))

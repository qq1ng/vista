from core import manifest
from core import validate


def make_shot(name, frame_start, frame_end):
    return manifest.build_shot(name, f"{name}.fbx", frame_start, frame_end, 35.0, 1.41732, 0.94488)


def make_manifest(shots, characters=None, scene_start=1, scene_end=120):
    if characters is None:
        characters = []
    scene = manifest.build_scene("test", scene_start, scene_end, 24.0)
    return manifest.build_manifest(scene, shots, characters)


def levels(issues):
    result = []
    for issue in issues:
        result.append(issue["level"])
    return result


def test_clean_manifest_has_no_issues():
    data = make_manifest([make_shot("A", 1, 60), make_shot("B", 61, 120)])
    assert validate.validate_manifest(data) == []


def test_no_shots_is_an_error():
    issues = validate.validate_manifest(make_manifest([]))
    assert validate.has_errors(issues)


def test_names_that_collide_as_files_are_an_error():
    data = make_manifest([make_shot("grp|cam", 1, 60), make_shot("grp:cam", 61, 120)])
    issues = validate.check_unique_names(data)
    assert levels(issues) == [validate.ERROR]


def test_camera_and_character_with_same_name_are_an_error():
    character = manifest.build_character("hero", "hero.fbx", 1, 120)
    data = make_manifest([make_shot("hero", 1, 60)], [character])
    assert validate.has_errors(validate.check_unique_names(data))


def test_overlap_is_a_warning():
    data = make_manifest([make_shot("A", 1, 70), make_shot("B", 61, 120)])
    issues = validate.check_overlaps(data)
    assert levels(issues) == [validate.WARNING]


def test_shot_outside_scene_range_is_a_warning():
    data = make_manifest([make_shot("A", 130, 150)])
    issues = validate.check_shot_ranges(data)
    assert levels(issues) == [validate.WARNING]


def test_shot_partly_outside_scene_range_is_a_warning():
    data = make_manifest([make_shot("A", 100, 130)])
    issues = validate.check_shot_ranges(data)
    assert levels(issues) == [validate.WARNING]


def test_warnings_alone_do_not_stop_the_export():
    issues = [validate.make_issue(validate.WARNING, "x"), validate.make_issue(validate.INFO, "y")]
    assert not validate.has_errors(issues)


def test_filmback_preset_matches_within_tolerance():
    presets = [("16:9 Digital Film", 23.76, 13.365), ("Full Frame DSLR", 36.0, 24.0)]
    assert validate.find_filmback_preset(35.999928, 23.999952, presets) == "Full Frame DSLR"


def test_filmback_preset_none_when_nothing_matches():
    presets = [("16:9 Digital Film", 23.76, 13.365)]
    assert validate.find_filmback_preset(36.0, 24.0, presets) is None


def test_missing_fbx_file_is_an_error(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    (tmp_path / "A.fbx").write_text("fbx", encoding="utf-8")
    data = make_manifest([make_shot("A", 1, 60), make_shot("B", 61, 120)])
    issues = validate.check_files_exist(data, manifest_path)
    assert levels(issues) == [validate.ERROR]
    assert "'B'" in issues[0]["message"]


def test_summarize_issues_counts_levels():
    issues = [
        validate.make_issue(validate.ERROR, "a"),
        validate.make_issue(validate.WARNING, "b"),
        validate.make_issue(validate.WARNING, "c"),
        validate.make_issue(validate.INFO, "d"),
    ]
    assert validate.summarize_issues(issues) == "1 error, 2 warnings"


def test_summarize_no_issues():
    assert validate.summarize_issues([]) == "0 errors, 0 warnings"


def test_format_issue():
    issue = validate.make_issue(validate.ERROR, "Broken.")
    assert validate.format_issue(issue) == "[ERROR] Broken."

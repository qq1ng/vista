from core import cuts
from core import manifest


def make_shot(name, frame_start, frame_end):
    return manifest.build_shot(name, f"{name}.fbx", frame_start, frame_end, 35.0, 1.41732, 0.94488)


def make_manifest(shots, scene_start=1, scene_end=120):
    scene = manifest.build_scene("test", scene_start, scene_end, 24.0)
    return manifest.build_manifest(scene, shots, [])


def test_two_shots_cover_the_whole_scene():
    data = make_manifest([make_shot("A", 1, 60), make_shot("B", 61, 110)])
    assert cuts.build_cut_list(data) == [
        {"shot": "A", "frame_start": 1, "frame_end": 60},
        {"shot": "B", "frame_start": 61, "frame_end": 120},
    ]


def test_gap_between_shots_holds_previous_camera():
    data = make_manifest([make_shot("A", 1, 50), make_shot("B", 61, 120)])
    cut_list = cuts.build_cut_list(data)
    assert cut_list[0]["frame_end"] == 60


def test_first_cut_starts_at_scene_start():
    data = make_manifest([make_shot("A", 10, 60)])
    assert cuts.build_cut_list(data)[0]["frame_start"] == 1


def test_shots_sort_by_start_frame_not_list_order():
    data = make_manifest([make_shot("B", 61, 120), make_shot("A", 1, 60)])
    cut_list = cuts.build_cut_list(data)
    assert cut_list[0]["shot"] == "A"
    assert cut_list[1]["shot"] == "B"


def test_same_start_gives_one_cut():
    data = make_manifest([make_shot("A", 1, 60), make_shot("B", 1, 60)])
    cut_list = cuts.build_cut_list(data)
    assert len(cut_list) == 1
    assert cut_list[0]["shot"] == "B"


def test_no_shots_gives_no_cuts():
    assert cuts.build_cut_list(make_manifest([])) == []

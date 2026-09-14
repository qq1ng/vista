import unreal
from core import cuts
from core import manifest
from core import validate


DESTINATION = "/Game/Vista"
INTERCHANGE_FBX = "Interchange.FeatureFlags.Import.FBX"


# sends each issue to the Output Log at matching level
def log_issues(issues):
    for issue in issues:
        text = "Vista: " + validate.format_issue(issue)
        if issue["level"] == validate.ERROR:
            unreal.log_error(text)
        elif issue["level"] == validate.WARNING:
            unreal.log_warning(text)
        else:
            unreal.log(text)


# switches FBX import to the legacy importer, returns True if Interchange was on
# Interchange imports a camera-only FBX as "no data", and the flag resets on every editor start
def use_legacy_fbx_import():
    interchange_was_on = unreal.SystemLibrary.get_console_variable_bool_value(INTERCHANGE_FBX)
    if interchange_was_on:
        unreal.log_warning(
            "Vista: Interchange FBX import is on. Vista switches to the legacy FBX importer "
            "for this build, then switches it back."
        )
        unreal.SystemLibrary.execute_console_command(None, f"{INTERCHANGE_FBX} 0")
    return interchange_was_on


# puts the FBX importer back the way the artist had it
def restore_fbx_import(interchange_was_on):
    if interchange_was_on:
        unreal.SystemLibrary.execute_console_command(None, f"{INTERCHANGE_FBX} 1")


# the filmback presets Unreal knows, as (name, width_mm, height_mm) tuples for core
def get_filmback_presets():
    presets = []
    for preset in unreal.CineCameraComponent.get_filmback_presets_copy():
        filmback = preset.get_editor_property("filmback_settings")
        presets.append((preset.get_editor_property("name"), filmback.sensor_width, filmback.sensor_height))
    return presets


# removes every binding and every track, so a rebuild starts from nothing
def clear_sequence(sequence):
    for binding in sequence.get_bindings():
        binding.remove()
    for track in sequence.get_tracks():
        sequence.remove_track(track)


# returns an empty Level Sequence with this name
# an existing one is cleared and reused, not deleted: Unreal cannot delete a package that is
# still loaded, and a level that plays the sequence keeps its link
def get_empty_sequence(sequence_name):
    asset_path = f"{DESTINATION}/{sequence_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        sequence = unreal.load_asset(asset_path)
        clear_sequence(sequence)
        return sequence

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    sequence = asset_tools.create_asset(
        asset_name=sequence_name,
        package_path=DESTINATION,
        asset_class=unreal.LevelSequence,
        factory=unreal.LevelSequenceFactoryNew(),
    )
    return sequence


# display rate and playback range from the manifest scene
# Unreal ranges exclude the end frame, so Maya's last frame 120 becomes end 121
def set_sequence_timing(sequence, scene):
    numerator, denominator = manifest.fps_to_fraction(scene["fps"])
    sequence.set_display_rate(unreal.FrameRate(numerator, denominator))
    sequence.set_playback_start(scene["frame_start"])
    sequence.set_playback_end(scene["frame_end"] + 1)

    start_seconds = scene["frame_start"] / scene["fps"]
    end_seconds = (scene["frame_end"] + 1) / scene["fps"]
    sequence.set_work_range_start(start_seconds)
    sequence.set_work_range_end(end_seconds)
    sequence.set_view_range_start(start_seconds)
    sequence.set_view_range_end(end_seconds)


# focal length, filmback and focus on one camera actor
# filmback and focus settings are structs, so build-fill-assign
def apply_lens(camera_actor, shot):
    component = camera_actor.camera_component
    component.current_focal_length = shot["focal_length"]

    filmback = unreal.CameraFilmbackSettings()
    filmback.sensor_width = shot["sensor_width_mm"]
    filmback.sensor_height = shot["sensor_height_mm"]
    component.filmback = filmback

    # Maya's default focus distance is 5 cm, and the FBX import writes it as a focus track
    # with depth of field off in Maya, Unreal must not blur the shot with that value
    focus = component.get_editor_property("focus_settings")
    if shot["depth_of_field"]:
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.MANUAL)
    else:
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
    component.set_editor_property("focus_settings", focus)


# adds one camera for one shot: binding, FBX animation, then lens and filmback
def add_shot_camera(sequence, shot, manifest_path, world):
    ls_system = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    binding, camera_actor = ls_system.create_camera(spawnable=True)
    binding.set_name(shot["name"])

    settings = unreal.MovieSceneUserImportFBXSettings()
    settings.set_editor_property("match_by_name_only", False)
    settings.set_editor_property("replace_transform_track", True)
    settings.set_editor_property("convert_scene_unit", True)
    settings.set_editor_property("create_cameras", False)

    fbx_path = manifest.resolve_path(shot["fbx_path"], manifest_path)
    imported = unreal.SequencerTools.import_level_sequence_fbx(world, sequence, [binding], settings, fbx_path)
    if not imported:
        unreal.log_error(f"Vista: shot '{shot['name']}': the FBX import failed for {fbx_path}")

    # the lens goes on after the import, so the manifest has the last word
    # the spawned actor shows it now, the template keeps it after the sequence closes
    apply_lens(camera_actor, shot)
    template = binding.get_object_template()
    if isinstance(template, unreal.CineCameraActor):
        apply_lens(template, shot)
    return binding


# replaces every cut on the Camera Cut Track with one cut per entry in the cut list
# create_camera adds its own cut each time, so those cuts go first
def build_camera_cuts(sequence, cut_list, bindings_by_name):
    tracks = sequence.find_tracks_by_type(unreal.MovieSceneCameraCutTrack)
    if len(tracks) == 0:
        track = sequence.add_track(unreal.MovieSceneCameraCutTrack)
    else:
        track = tracks[0]

    for section in track.get_sections():
        track.remove_section(section)

    for cut in cut_list:
        binding = bindings_by_name[cut["shot"]]
        section = track.add_section()
        section.set_camera_binding_id(sequence.get_binding_id(binding))
        section.set_range(cut["frame_start"], cut["frame_end"] + 1)


# runs one legacy FBX import task, saves what it makes
def run_import_task(fbx_path, destination, options):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", fbx_path)
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])


# loads the first asset of a class from one folder, or None
def find_asset(folder, asset_class):
    for asset_path in unreal.EditorAssetLibrary.list_assets(folder, recursive=False):
        asset = unreal.load_asset(asset_path)
        if isinstance(asset, asset_class):
            return asset
    return None


# imports the skinned mesh of a character FBX, returns the SkeletalMesh or None
def import_character_mesh(fbx_path, folder):
    options = unreal.FbxImportUI()
    options.set_editor_property("automated_import_should_detect_type", False)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_animations", False)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_textures", True)
    options.set_editor_property("create_physics_asset", False)
    run_import_task(fbx_path, folder, options)
    return find_asset(folder, unreal.SkeletalMesh)


# imports the baked animation of a character FBX onto an existing skeleton, returns the AnimSequence or None
def import_character_animation(fbx_path, folder, skeleton):
    options = unreal.FbxImportUI()
    options.set_editor_property("automated_import_should_detect_type", False)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    options.set_editor_property("import_mesh", False)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_animations", True)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("skeleton", skeleton)
    run_import_task(fbx_path, folder, options)
    return find_asset(folder, unreal.AnimSequence)


# makes a spawnable from an asset the way the Sequencer menu does it:
# place a level actor, add it to the open sequence, convert it to a spawnable
# add_spawnable_from_instance makes a 5.5 custom binding that never spawns a skeletal mesh
def add_spawnable_actor(asset, name):
    actor_system = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actor_system.spawn_actor_from_object(asset, unreal.Vector(0.0, 0.0, 0.0))
    actor.set_actor_label(name)

    ls_system = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    possessable = ls_system.add_actors([actor])[0]
    spawnable = ls_system.convert_to_spawnable(possessable)[0]
    return spawnable


# adds one character: a spawnable skeletal mesh with its animation on a Skeletal Animation Track
def add_character(sequence, character, manifest_path):
    fbx_path = manifest.resolve_path(character["fbx_path"], manifest_path)
    folder = f"{DESTINATION}/Characters/{manifest.safe_name(character['name'])}"

    # two imports, two folders: the mesh first, then the animation onto the mesh's skeleton
    skeletal_mesh = import_character_mesh(fbx_path, folder)
    if skeletal_mesh is None:
        unreal.log_error(f"Vista: character '{character['name']}': the FBX import made no skeletal mesh.")
        return None
    skeleton = skeletal_mesh.get_editor_property("skeleton")
    animation = import_character_animation(fbx_path, f"{folder}/Animations", skeleton)

    binding = add_spawnable_actor(skeletal_mesh, character["name"])
    binding.set_name(character["name"])

    if animation is None:
        unreal.log_warning(f"Vista: character '{character['name']}': the FBX holds no animation. It stands in its bind pose.")
        return binding

    # Sequencer adds default tracks to a new actor binding, an empty animation track among them
    # so the same find-or-add, then clear, as the Camera Cut Track
    tracks = binding.find_tracks_by_type(unreal.MovieSceneSkeletalAnimationTrack)
    if len(tracks) == 0:
        track = binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    else:
        track = tracks[0]
    for extra_track in tracks[1:]:
        binding.remove_track(extra_track)
    for old_section in track.get_sections():
        track.remove_section(old_section)

    section = track.add_section()
    section.set_range(character["frame_start"], character["frame_end"] + 1)

    # params is a struct, so build-fill-assign again
    params = section.get_editor_property("params")
    params.set_editor_property("animation", animation)
    section.set_editor_property("params", params)
    return binding


# fills the sequence: timing, one camera per shot, the cuts, the characters
def build_sequence(manifest_data, manifest_path):
    scene = manifest_data["scene"]
    sequence = get_empty_sequence(f"LS_{manifest.safe_name(scene['name'])}")
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    set_sequence_timing(sequence, scene)

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    bindings_by_name = {}
    for shot in manifest_data["shots"]:
        bindings_by_name[shot["name"]] = add_shot_camera(sequence, shot, manifest_path, world)

    build_camera_cuts(sequence, cuts.build_cut_list(manifest_data), bindings_by_name)

    for character in manifest_data["characters"]:
        add_character(sequence, character, manifest_path)

    unreal.EditorAssetLibrary.save_loaded_asset(sequence, False)
    return sequence


# after a build: the playhead on the first frame, and optionally the viewport through the shot cameras
# Unreal does not lock the viewport to the camera cuts by itself, so artists see no camera view
def show_first_frame(scene, lock_viewport):
    sequencer = unreal.LevelSequenceEditorBlueprintLibrary
    sequencer.set_current_time(scene["frame_start"])
    if lock_viewport:
        sequencer.set_lock_camera_cut_to_viewport(True)


# builds the whole Level Sequence from a manifest file
# returns the sequence, or None when a rule failed and nothing was built
def build_from_manifest(manifest_path, lock_viewport=True):
    manifest_path = manifest_path.replace("\\", "/")
    manifest_data = manifest.read_manifest(manifest_path)

    issues = validate.validate_manifest(manifest_data)
    issues.extend(validate.check_files_exist(manifest_data, manifest_path))
    issues.extend(validate.check_filmback_presets(manifest_data, get_filmback_presets()))
    log_issues(issues)
    if validate.has_errors(issues):
        unreal.log_error("Vista: the manifest has errors. Nothing was built.")
        return None

    interchange_was_on = use_legacy_fbx_import()
    try:
        sequence = build_sequence(manifest_data, manifest_path)
    finally:
        restore_fbx_import(interchange_was_on)

    show_first_frame(manifest_data["scene"], lock_viewport)
    unreal.log(
        f"Vista: built {sequence.get_path_name()} with {len(manifest_data['shots'])} shots "
        f"and {len(manifest_data['characters'])} characters."
    )
    return sequence

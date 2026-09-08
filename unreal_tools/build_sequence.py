import unreal
from core import manifest

def build_from_manifest(manifest_path):
    manifest_file = manifest.read_manifest(manifest_path)
    shot = manifest_file["shots"][0]
    #task = unreal.AssetImportTask()
    #task.filename = shot["fbx_path"]
    #task.destination_path = "/Game/Vista"
    #task.automated = True
    #task.replace_existing = True
    #task.save = True
    #unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    sequence = asset_tools.create_asset(
        asset_name = "Manifest_Sequence", #NOTE: change later
        package_path = "/Game/Vista",
        asset_class = unreal.LevelSequence,
        factory = unreal.LevelSequenceFactoryNew()
    )

    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    sequence.set_playback_start(int(shot["frame_start"]))
    sequence.set_playback_end(int(shot["frame_end"]))

    ls_system = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    binding, camera_actor = ls_system.create_camera(spawnable = True)

    component = camera_actor.camera_component
    component.current_focal_length = shot["focal_length"]
    fb = unreal.CameraFilmbackSettings()
    fb.sensor_width = shot["sensor_width_mm"]
    fb.sensor_height = shot["sensor_height_mm"]
    component.filmback = fb
    
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()

    settings = unreal.MovieSceneUserImportFBXSettings()
    settings.set_editor_property("match_by_name_only", False)
    settings.set_editor_property("replace_transform_track", True)
    settings.set_editor_property("convert_scene_unit", True)

    binding.set_name(shot["name"])                                  
    settings.set_editor_property("create_cameras", False)

    ok = unreal.SequencerTools.import_level_sequence_fbx(
        world, sequence, [binding], settings, shot["fbx_path"]
    )
    print("fbx import:", ok)






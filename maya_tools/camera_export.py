import maya.mel as mel
import maya.cmds as cmds
from core import manifest


# output cameras in scene and print shape, name, pos, rot, fl, aperture 
def print_all_cameras():
    for shape in cmds.ls(type="camera"):
        transform = cmds.listRelatives(shape, parent=True)[0]
        position = cmds.getAttr(f"{transform}.translate")
        rotation = cmds.getAttr(f"{transform}.rotate")
        focal_length = cmds.getAttr(f"{shape}.focalLength")
        horizontal_film_aperture = cmds.getAttr(f"{shape}.horizontalFilmAperture")
        vertical_film_aperture = cmds.getAttr(f"{shape}.verticalFilmAperture")
        print(shape, transform, position, rotation, focal_length, horizontal_film_aperture, vertical_film_aperture)


# creating a dict for each required datapoint. key_first/last gives 1 for each if cam is unkeyed
def print_keyframe_data():
    for shape in cmds.ls(type="camera"):
        if not cmds.camera(shape, query=True, startupCamera=True):


            transform = cmds.listRelatives(shape, parent=True)[0]

            # list of touples of plugs we want to check
            plugs = [
                (transform, "translateX"),
                (transform, "translateY"),
                (transform, "translateZ"),
                (transform, "rotateX"),
                (transform, "rotateY"),
                (transform, "rotateZ"),
                (shape, "focalLength"),
            ]

            # dict of keyframe times per plug
            times = {}
            for node, attribute in plugs:
                plug = f"{node}.{attribute}"
                times[attribute] = cmds.keyframe(plug, query=True, timeChange=True)

            # dict of keyframe values per plug
            values = {}
            for node, attribute in plugs:
                plug = f"{node}.{attribute}"
                values[attribute] = cmds.keyframe(plug, query=True, valueChange=True)

            # dict of keyframe amount per plug
            key_count = {}
            for node, attribute in plugs:
                plug = f"{node}.{attribute}"
                key_count[attribute] = cmds.keyframe(plug, query=True, keyframeCount=True)

            key_first = {}
            for node, attribute in plugs:
                plug = f"{node}.{attribute}"
                key_first[attribute] = cmds.findKeyframe(plug, which="first")

            key_last = {}
            for node, attribute in plugs:
                plug = f"{node}.{attribute}"
                key_last[attribute] = cmds.findKeyframe(plug, which="last")
            
            print("TIMES:", times, "VALUES:", values, "KEY AMOUNT:", key_count, "FIRST KEY:", key_first, "LAST KEY:", key_last,)


# exports cam with keyframes baked out to path
def export_camera(camera_transform, fbx_path):
    mel.eval("FBXResetExport;") 

    scene_start = cmds.playbackOptions(query=True, minTime=True)
    scene_end = cmds.playbackOptions(query=True, maxTime=True)

    mel.eval("FBXExportBakeComplexAnimation -v true;")
    mel.eval(f"FBXExportBakeComplexStart -v {scene_start};")
    mel.eval(f"FBXExportBakeComplexEnd -v {scene_end};")
    mel.eval("FBXExportBakeComplexStep -v 1;")
    mel.eval("FBXExportCameras -v true;")
    cmds.select(camera_transform)
    mel.eval(f'FBXExport -f "{fbx_path}" -s;')

    return {
    "fbx_path": fbx_path,
    "frame_start": scene_start,
    "frame_end": scene_end,
    }


# assembles and writes shot json using core manifest, exports baked camera fbx
def export_shot(camera_transform, fbx_path, manifest_path):
    shape = cmds.listRelatives(camera_transform, shapes=True)[0]
    focal_length = cmds.getAttr(f"{shape}.focalLength")
    horizontal_film_aperture = cmds.getAttr(f"{shape}.horizontalFilmAperture")
    vertical_film_aperture = cmds.getAttr(f"{shape}.verticalFilmAperture")

    fbx_result = export_camera(camera_transform, fbx_path)
    shot = manifest.build_shot(
        camera_transform,
        fbx_path, 
        fbx_result["frame_start"], 
        fbx_result["frame_end"], 
        focal_length, 
        horizontal_film_aperture, 
        vertical_film_aperture
        )
    manifest.write_manifest([shot], manifest_path)

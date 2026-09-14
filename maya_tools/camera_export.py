import maya.mel as mel
import maya.cmds as cmds
from maya_tools import fbx_utils


# returns the transform of every camera the artist made, skips persp, top, front and side
def get_export_cameras():
    cameras = []
    for shape in cmds.ls(type="camera"):
        if not cmds.camera(shape, query=True, startupCamera=True):
            transform = cmds.listRelatives(shape, parent=True)[0]
            cameras.append(transform)
    return cameras


# returns the camera shape under a camera transform
def get_camera_shape(camera_transform):
    return cmds.listRelatives(camera_transform, shapes=True, type="camera")[0]


# list of (node, attribute) tuples, the seven channels the FBX carries
def get_camera_plugs(camera_transform):
    shape = get_camera_shape(camera_transform)
    plugs = [
        (camera_transform, "translateX"),
        (camera_transform, "translateY"),
        (camera_transform, "translateZ"),
        (camera_transform, "rotateX"),
        (camera_transform, "rotateY"),
        (camera_transform, "rotateZ"),
        (shape, "focalLength"),
    ]
    return plugs


# one dict per channel holding everything known about its keys
# first and last stay None on unkeyed channels, because findKeyframe returns 1.0 there
def get_keyframe_data(camera_transform):
    channels = {}
    for node, attribute in get_camera_plugs(camera_transform):
        plug = f"{node}.{attribute}"
        count = cmds.keyframe(plug, query=True, keyframeCount=True)
        channel = {
            "count": count,
            "times": [],
            "values": [],
            "first": None,
            "last": None,
        }
        if count > 0:
            channel["times"] = cmds.keyframe(plug, query=True, timeChange=True)
            channel["values"] = cmds.keyframe(plug, query=True, valueChange=True)
            channel["first"] = cmds.findKeyframe(plug, which="first")
            channel["last"] = cmds.findKeyframe(plug, which="last")
        channels[attribute] = channel
    return channels


# first and last key over all seven channels, None if camera has no keys
def get_key_range(camera_transform):
    firsts = []
    lasts = []
    channels = get_keyframe_data(camera_transform)
    for channel in channels.values():
        if channel["count"] > 0:
            firsts.append(channel["first"])
            lasts.append(channel["last"])

    if len(firsts) == 0:
        return None
    return min(firsts), max(lasts)


# lens values at one frame, aperture stays in inches like Maya stores it
def get_lens(camera_transform, frame):
    shape = get_camera_shape(camera_transform)
    lens = {
        "focal_length": cmds.getAttr(f"{shape}.focalLength", time=frame),
        "horizontal_film_aperture": cmds.getAttr(f"{shape}.horizontalFilmAperture", time=frame),
        "vertical_film_aperture": cmds.getAttr(f"{shape}.verticalFilmAperture", time=frame),
        "depth_of_field": cmds.getAttr(f"{shape}.depthOfField", time=frame),
    }
    return lens


# exports one camera with its keys baked over the given range
def export_camera(camera_transform, fbx_path, frame_start, frame_end):
    fbx_utils.reset_fbx_export(frame_start, frame_end)
    mel.eval("FBXExportCameras -v true;")
    fbx_utils.export_nodes([camera_transform], fbx_path)

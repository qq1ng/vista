# Builds a test scene from nothing: a small set, two keyed cameras, one unkeyed camera,
# and optionally one Mixamo character with one or two clips.
#
# In the Maya Script Editor:
#   from examples import build_demo_scene
#   build_demo_scene.build_demo_scene()
#   build_demo_scene.build_demo_scene("C:/path/Ch36_nonPBR.fbx", "C:/path/Walk Strafe Left.fbx", "C:/path/Bboy Uprock Start.fbx")

import math
import maya.mel as mel
import maya.cmds as cmds
from maya_tools import fbx_utils


SCENE_START = 1
SCENE_END = 120
SECOND_CLIP_START = 61     # the cut to shot B
TARGET = (0.0, 100.0, 0.0)

# Maya stores film aperture in inches
FULL_FRAME_APERTURE = (1.41732, 0.94488)   # 36 x 24 mm
FILM_16_9_APERTURE = (0.94488, 0.53150)    # 24 x 13.5 mm


# rotation that points a Maya camera at a target, Maya cameras look down -Z
def look_at_rotation(position, target):
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    dz = target[2] - position[2]
    horizontal = math.sqrt(dx * dx + dz * dz)
    rotate_x = math.degrees(math.atan2(dy, horizontal))
    rotate_y = math.degrees(math.atan2(-dx, -dz))
    return rotate_x, rotate_y


# a ground plane and a few blocks
def build_set():
    nodes = []
    ground = cmds.polyPlane(name="ground", width=3000, height=3000)[0]
    nodes.append(ground)

    blocks = [
        (-300, 100, -400, 200),
        (350, 75, -250, 150),
        (-450, 50, 200, 100),
        (250, 150, 350, 300),
    ]
    for index in range(len(blocks)):
        x, y, z, size = blocks[index]
        block = cmds.polyCube(name=f"block_{index + 1}", width=size, height=y * 2, depth=size)[0]
        cmds.move(x, y, z, block)
        nodes.append(block)

    cmds.group(nodes, name="set_GRP")


# makes camera with a given name and film aperture
def build_camera(name, aperture):
    transform = cmds.camera()[0]
    transform = cmds.rename(transform, name)
    shape = cmds.listRelatives(transform, shapes=True)[0]
    cmds.setAttr(f"{shape}.horizontalFilmAperture", aperture[0])
    cmds.setAttr(f"{shape}.verticalFilmAperture", aperture[1])
    return transform, shape


# keys all seven channels of a camera at one frame, aimed at the target
def key_camera(transform, shape, frame, position, focal_length):
    rotate_x, rotate_y = look_at_rotation(position, TARGET)
    values = {
        "translateX": position[0],
        "translateY": position[1],
        "translateZ": position[2],
        "rotateX": rotate_x,
        "rotateY": rotate_y,
        "rotateZ": 0.0,
    }
    for attribute, value in values.items():
        cmds.setKeyframe(transform, attribute=attribute, time=frame, value=value)
    cmds.setKeyframe(shape, attribute="focalLength", time=frame, value=focal_length)


# replaces the animation on the scene's joints with the clip's animation
# exmerge: keep the nodes in the scene, replace their animation with the file's
def merge_clip(clip_fbx):
    mel.eval("FBXImportMode -v exmerge;")
    mel.eval(f'FBXImport -f "{clip_fbx}";')
    mel.eval("FBXImportMode -v add;")


# imports a Mixamo character, then puts one or two clips on its skeleton
# a merge replaces all animation, so two clips go through the key clipboard:
# merge the second clip first, copy its keys, merge the first clip, paste the keys back
def import_character(character_fbx, first_clip_fbx, second_clip_fbx):
    fbx_utils.load_fbx_plugin()
    mel.eval("FBXResetImport;")
    mel.eval(f'FBXImport -f "{character_fbx}";')
    joints = cmds.ls(type="joint")

    if second_clip_fbx:
        merge_clip(second_clip_fbx)
        # a clip starts at frame 0 in its file
        cmds.keyframe(joints, edit=True, relative=True, timeChange=SECOND_CLIP_START)
        cmds.copyKey(joints)

    if first_clip_fbx:
        merge_clip(first_clip_fbx)
        cmds.keyframe(joints, edit=True, relative=True, timeChange=SCENE_START)

    if first_clip_fbx and second_clip_fbx:
        # hold the first clip's last pose until the second clip starts, no slide in between
        last_key = max(cmds.keyframe(joints, query=True, timeChange=True))
        cmds.keyTangent(joints, time=(last_key, last_key), outTangentType="step")
        cmds.pasteKey(joints, option="merge", time=(SECOND_CLIP_START, SECOND_CLIP_START))


# builds the whole demo scene in a new file
def build_demo_scene(character_fbx=None, first_clip_fbx=None, second_clip_fbx=None):
    cmds.file(new=True, force=True)

    if character_fbx:
        import_character(character_fbx, first_clip_fbx, second_clip_fbx)

    # 30 fps, Mixamo clips are 30 fps
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(minTime=SCENE_START, maxTime=SCENE_END,
                         animationStartTime=SCENE_START, animationEndTime=SCENE_END)

    build_set()

    # shot A: a wide move pushing in, frames 1 to 60
    transform, shape = build_camera("shotCam_A", FULL_FRAME_APERTURE)
    key_camera(transform, shape, 1, (0, 160, 700), 28)
    key_camera(transform, shape, 30, (350, 140, 550), 32)
    key_camera(transform, shape, 60, (500, 120, 250), 35)

    # shot B: a long-lens close-up, frames 61 to 110
    # the last key sits before the scene end, the cut holds this camera to frame 120
    transform, shape = build_camera("shotCam_B", FILM_16_9_APERTURE)
    key_camera(transform, shape, 61, (-150, 170, 300), 85)
    key_camera(transform, shape, 110, (-80, 110, 220), 70)

    # a camera with no keys: the export must skip it and say so
    transform, shape = build_camera("unkeyedCam", FULL_FRAME_APERTURE)
    cmds.move(0, 500, 1000, transform)

    cmds.currentTime(SCENE_START)

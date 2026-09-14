import maya.mel as mel
import maya.cmds as cmds
from maya_tools import fbx_utils


# strips the path and the namespace, "grp|mixamorig1:Hips" gives "Hips"
def short_name(node):
    without_path = node.split("|")[-1]
    return without_path.split(":")[-1]


# walks up the parents of a joint until the parent is no longer a joint
def find_root_joint(joint):
    root = joint
    parents = cmds.listRelatives(root, parent=True, type="joint")
    while parents:
        root = parents[0]
        parents = cmds.listRelatives(root, parent=True, type="joint")
    return root


# finds every skinned character: its root joint and the meshes skinned to it
# one character can have many skinClusters, for example a body and a separate head
def get_characters():
    by_root = {}
    for skin_cluster in cmds.ls(type="skinCluster"):
        joints = cmds.skinCluster(skin_cluster, query=True, influence=True)
        root_joint = find_root_joint(joints[0])

        if root_joint not in by_root:
            by_root[root_joint] = {"name": "", "root_joint": root_joint, "meshes": []}
        character = by_root[root_joint]

        for shape in cmds.skinCluster(skin_cluster, query=True, geometry=True):
            mesh = cmds.listRelatives(shape, parent=True)[0]
            if mesh not in character["meshes"]:
                character["meshes"].append(mesh)

    characters = []
    for root_joint, character in by_root.items():
        character["name"] = short_name(character["meshes"][0])
        characters.append(character)
    return characters


# exports one character: skeleton, skinned meshes and the animation baked over the given range
def export_character(character, fbx_path, frame_start, frame_end):
    fbx_utils.reset_fbx_export(frame_start, frame_end)
    mel.eval("FBXExportSkins -v true;")
    mel.eval("FBXExportShapes -v true;")
    mel.eval("FBXExportSmoothingGroups -v true;")
    mel.eval("FBXExportCameras -v false;")
    mel.eval("FBXExportLights -v false;")
    nodes = [character["root_joint"]] + character["meshes"]
    fbx_utils.export_nodes(nodes, fbx_path)

import maya.cmds as cmds
import maya.mel as mel


# loads the FBX plugin, Maya window loads it at startup but mayapy does not
def load_fbx_plugin():
    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya")


# resets every FBX export setting, then bakes all animation over the given range
def reset_fbx_export(frame_start, frame_end):
    mel.eval("FBXResetExport;")
    mel.eval("FBXExportBakeComplexAnimation -v true;")
    mel.eval(f"FBXExportBakeComplexStart -v {frame_start};")
    mel.eval(f"FBXExportBakeComplexEnd -v {frame_end};")
    mel.eval("FBXExportBakeComplexStep -v 1;")


# exports the given nodes to FBX, then returns selection to previous state
def export_nodes(nodes, fbx_path):
    fbx_path = fbx_path.replace("\\", "/")
    saved_selection = cmds.ls(selection=True)
    try:
        cmds.select(nodes, replace=True)
        mel.eval(f'FBXExport -f "{fbx_path}" -s;')
    finally:
        if saved_selection:
            cmds.select(saved_selection, replace=True)
        else:
            cmds.select(clear=True)

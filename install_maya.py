# Drag this file into the Maya viewport to install vista.
# It puts the repository on Maya's Python path through userSetup.py,
# and adds a Vista button to the current shelf.

import os
import sys
import maya.cmds as cmds
import maya.mel as mel


REPO_ROOT = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
BUTTON_LABEL = "Vista"
BUTTON_COMMAND = "from maya_tools import ui\nui.show()"


# the userSetup.py Maya runs at startup, in the scripts folder of this Maya version
def get_user_setup_path():
    maya_folder = cmds.internalVar(userAppDir=True)
    version = cmds.about(version=True)
    return f"{maya_folder}{version}/scripts/userSetup.py"


# adds the repository path to userSetup.py, one time only, and keeps what is already in the file
# returns True when it added the lines, False when they were there already
def add_to_user_setup(user_setup_path, repo_root):
    text = ""
    if os.path.isfile(user_setup_path):
        with open(user_setup_path, "r", encoding="utf-8") as f:
            text = f.read()
    if repo_root in text:
        return False

    lines = (
        "\n# vista: put the repository on the Python path\n"
        "import sys\n"
        f'if "{repo_root}" not in sys.path:\n'
        f'    sys.path.append("{repo_root}")\n'
    )
    os.makedirs(os.path.dirname(user_setup_path), exist_ok=True)
    with open(user_setup_path, "a", encoding="utf-8") as f:
        f.write(lines)
    return True


# adds a Vista button to the current shelf, and removes an older Vista button there first
# returns the shelf name
def add_shelf_button():
    shelf_top_level = mel.eval("$vistaShelfTopLevel = $gShelfTopLevel")
    shelf = cmds.tabLayout(shelf_top_level, query=True, selectTab=True)

    children = cmds.shelfLayout(shelf, query=True, childArray=True)
    if children:
        for child in children:
            if cmds.shelfButton(child, exists=True):
                if cmds.shelfButton(child, query=True, label=True) == BUTTON_LABEL:
                    cmds.deleteUI(child)

    cmds.shelfButton(
        parent=shelf,
        label=BUTTON_LABEL,
        imageOverlayLabel=BUTTON_LABEL,
        image="pythonFamily.png",
        annotation="Open the vista export window",
        sourceType="python",
        command=BUTTON_COMMAND,
    )
    mel.eval("saveAllShelves $gShelfTopLevel")
    return shelf


# installs vista: the Python path for this session and every later start, and the shelf button
def install():
    if REPO_ROOT not in sys.path:
        sys.path.append(REPO_ROOT)

    user_setup_path = get_user_setup_path()
    if add_to_user_setup(user_setup_path, REPO_ROOT):
        path_message = f"Added the vista path to {user_setup_path}."
    else:
        path_message = f"The vista path was already in {user_setup_path}."
    shelf = add_shelf_button()

    cmds.confirmDialog(
        title="vista",
        message=f"vista is installed.\n\n{path_message}\nThe shelf '{shelf}' has a new Vista button.",
        button=["OK"],
    )


# Maya calls this function when the file is dropped into the viewport
def onMayaDroppedPythonFile(*args):
    install()

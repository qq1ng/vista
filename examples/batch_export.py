# Batch export with no Maya window. Run with mayapy, not plain Python.
#
#   mayapy examples/batch_export.py <output_folder> <scene_file>
#   mayapy examples/batch_export.py <output_folder> --demo [character.fbx] [first_clip.fbx] [second_clip.fbx]
#
# --demo builds demo scene, saves as vista_demo.ma in the output folder, then exports.
# Exit code 0: manifest written. Exit code 1: a rule failed, nothing written.

import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

USAGE = (
    "usage: mayapy examples/batch_export.py <output_folder> <scene_file>\n"
    "       mayapy examples/batch_export.py <output_folder> --demo [character.fbx] [first_clip.fbx] [second_clip.fbx]"
)


def main(arguments):
    if len(arguments) < 2:
        print(USAGE)
        return 2
    output_folder = os.path.abspath(arguments[0]).replace("\\", "/")
    source = arguments[1]

    # maya.cmds works only after this call, so the Maya imports sit below it
    import maya.standalone
    maya.standalone.initialize(name="python")
    try:
        import maya.cmds as cmds
        from core import validate
        from maya_tools import scene_export
        from examples import build_demo_scene

        if source == "--demo":
            character_fbx = None
            first_clip_fbx = None
            second_clip_fbx = None
            if len(arguments) > 2:
                character_fbx = arguments[2]
            if len(arguments) > 3:
                first_clip_fbx = arguments[3]
            if len(arguments) > 4:
                second_clip_fbx = arguments[4]
            build_demo_scene.build_demo_scene(character_fbx, first_clip_fbx, second_clip_fbx)
            os.makedirs(output_folder, exist_ok=True)
            cmds.file(rename=f"{output_folder}/vista_demo.ma")
            cmds.file(save=True, type="mayaAscii")
        else:
            cmds.file(source, open=True, force=True)

        manifest_path, issues = scene_export.export_scene(output_folder)
        for issue in issues:
            print(validate.format_issue(issue))

        if manifest_path is None:
            print("Nothing written. Fix the errors above.")
            return 1
        print(f"Wrote {manifest_path}")
        return 0
    finally:
        maya.standalone.uninitialize()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# The dockable Vista export window.
#   from maya_tools import ui
#   ui.show()

import maya.cmds as cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# Maya 2025 and later ship PySide6, older Maya ships PySide2, the code below works with both
try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets

from core import validate
from maya_tools import camera_export
from maya_tools import character_export
from maya_tools import scene_export


WINDOW_NAME = "vistaExportWindow"
OUTPUT_FOLDER_OPTION = "vistaOutputFolder"
LEVEL_COLORS = {
    validate.ERROR: "#e06c6c",
    validate.WARNING: "#e0b050",
    validate.INFO: "#a0a0a0",
}


# the output folder from the last session, Maya keeps optionVars between sessions
def load_output_folder():
    if cmds.optionVar(exists=OUTPUT_FOLDER_OPTION):
        return cmds.optionVar(query=OUTPUT_FOLDER_OPTION)
    return ""


# remembers the output folder for the next session
def save_output_folder(folder):
    cmds.optionVar(stringValue=(OUTPUT_FOLDER_OPTION, folder))


# adds one checkbox row to a list, value is the Maya node the row stands for
def add_checkable_item(list_widget, label, value, checked):
    item = QtWidgets.QListWidgetItem(label)
    item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
    if checked:
        item.setCheckState(QtCore.Qt.CheckState.Checked)
    else:
        item.setCheckState(QtCore.Qt.CheckState.Unchecked)
    item.setData(QtCore.Qt.ItemDataRole.UserRole, value)
    list_widget.addItem(item)


# returns the stored value of every checked row
def checked_values(list_widget):
    values = []
    for row in range(list_widget.count()):
        item = list_widget.item(row)
        if item.checkState() == QtCore.Qt.CheckState.Checked:
            values.append(item.data(QtCore.Qt.ItemDataRole.UserRole))
    return values


# actual window: pick cameras and characters, pick a folder, check, export
class VistaWindow(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(WINDOW_NAME)
        self.setWindowTitle("Vista Export")
        self.build_layout()
        self.connect_signals()
        self.refresh()

    # creates every widget and puts it in a layout
    def build_layout(self):
        self.camera_list = QtWidgets.QListWidget()
        self.character_list = QtWidgets.QListWidget()
        self.folder_field = QtWidgets.QLineEdit(load_output_folder())
        self.browse_button = QtWidgets.QPushButton("Browse...")
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.check_button = QtWidgets.QPushButton("Check")
        self.export_button = QtWidgets.QPushButton("Export")
        self.message_list = QtWidgets.QListWidget()
        self.message_list.setWordWrap(True)

        folder_row = QtWidgets.QHBoxLayout()
        folder_row.addWidget(self.folder_field)
        folder_row.addWidget(self.browse_button)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.check_button)
        button_row.addWidget(self.export_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Cameras"))
        layout.addWidget(self.camera_list)
        layout.addWidget(QtWidgets.QLabel("Characters"))
        layout.addWidget(self.character_list)
        layout.addWidget(QtWidgets.QLabel("Output folder"))
        layout.addLayout(folder_row)
        layout.addLayout(button_row)
        layout.addWidget(QtWidgets.QLabel("Messages"))
        layout.addWidget(self.message_list)

    # tells Qt which method runs when a button is clicked
    def connect_signals(self):
        self.browse_button.clicked.connect(self.browse)
        self.refresh_button.clicked.connect(self.refresh)
        self.check_button.clicked.connect(self.check)
        self.export_button.clicked.connect(self.export)

    # fills both lists from the scene, keyed cameras start checked
    def refresh(self):
        self.camera_list.clear()
        for camera in camera_export.get_export_cameras():
            key_range = camera_export.get_key_range(camera)
            if key_range is None:
                label = f"{camera}   (no keys)"
            else:
                label = f"{camera}   frames {int(key_range[0])} to {int(key_range[1])}"
            add_checkable_item(self.camera_list, label, camera, key_range is not None)

        self.character_list.clear()
        for character in character_export.get_characters():
            add_checkable_item(self.character_list, character["name"], character["root_joint"], True)

        self.message_list.clear()

    # opens a folder picker and puts the result in the folder field
    def browse(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Output folder", self.folder_field.text())
        if folder:
            self.folder_field.setText(folder)

    # runs every rule, writes nothing
    def check(self):
        self.run_export(dry_run=True)

    # runs every rule, then exports when no rule failed
    def export(self):
        self.run_export(dry_run=False)

    # shared by check and export
    def run_export(self, dry_run):
        folder = self.folder_field.text().strip()
        if not folder:
            self.show_messages([validate.make_issue(validate.ERROR, "Pick an output folder first.")])
            return
        save_output_folder(folder)

        manifest_path, issues = scene_export.export_scene(
            folder,
            camera_transforms=checked_values(self.camera_list),
            character_roots=checked_values(self.character_list),
            dry_run=dry_run,
        )

        if manifest_path is not None:
            issues.append(validate.make_issue(validate.INFO, f"Wrote {manifest_path}"))
        elif dry_run and not validate.has_errors(issues):
            issues.append(validate.make_issue(validate.INFO, "Check passed. Nothing was written."))
        self.show_messages(issues)

    # one row per issue, colored by level
    def show_messages(self, issues):
        self.message_list.clear()
        for issue in issues:
            item = QtWidgets.QListWidgetItem(validate.format_issue(issue))
            item.setForeground(QtGui.QColor(LEVEL_COLORS[issue["level"]]))
            self.message_list.addItem(item)


# closes an old window, then opens a new docked one
def show():
    control_name = WINDOW_NAME + "WorkspaceControl"
    if cmds.workspaceControl(control_name, query=True, exists=True):
        cmds.deleteUI(control_name)
    window = VistaWindow()
    window.show(dockable=True)
    return window

import unreal


MENU_OWNER = "vista"
MENU_NAME = "LevelEditor.MainMenu.Vista"
SECTION = "Vista"


# one menu entry that runs one line of Python
def add_entry(menu, name, label, tool_tip, command):
    entry = unreal.ToolMenuEntry(name=name, type=unreal.MultiBlockType.MENU_ENTRY)
    entry.set_label(label)
    entry.set_tool_tip(tool_tip)
    entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, "", command)
    menu.add_menu_entry(SECTION, entry)


# adds the Vista menu to the main menu bar of the level editor
# a second call finds the menu that exists, and entries with the same name replace the old ones
def add_vista_menu():
    menus = unreal.ToolMenus.get()
    vista_menu = menus.find_menu(MENU_NAME)
    if vista_menu is None:
        main_menu = menus.find_menu("LevelEditor.MainMenu")
        vista_menu = main_menu.add_sub_menu(MENU_OWNER, "", "Vista", "Vista", "Maya to Unreal shot pipeline")
    vista_menu.add_section(SECTION, "Vista")

    add_entry(vista_menu, "OpenPanel", "Open Panel", "Open the Vista panel",
              "from unreal_tools import widget_actions; widget_actions.open_panel()")
    add_entry(vista_menu, "BuildLastExport", "Build Last Export",
              "Build the Level Sequence from the manifest Maya wrote last",
              "from unreal_tools import widget_actions; widget_actions.build('')")
    add_entry(vista_menu, "CheckLastExport", "Check Last Export",
              "Check the manifest Maya wrote last. Builds nothing",
              "from unreal_tools import widget_actions; widget_actions.check('')")
    menus.refresh_all_widgets()

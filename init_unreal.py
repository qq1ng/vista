# Unreal runs every init_unreal.py on its Python path at startup.
# With the vista folder in Project Settings > Plugins > Python > Additional Paths,
# this file adds the Vista menu to the main menu bar.

from unreal_tools import menu

menu.add_vista_menu()

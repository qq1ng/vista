import json
import os


# the small file that remembers the manifest Maya wrote last, shared by Maya and Unreal
# APPDATA is the same folder in both applications, "~" is not: Maya can set HOME to Documents
def get_last_export_file():
    folder = os.environ.get("APPDATA")
    if not folder:
        folder = os.path.expanduser("~")
    return os.path.join(folder, "vista", "last_export.json").replace("\\", "/")


# remembers a manifest path as the last export
def remember_last_export(manifest_path, last_export_file=None):
    if last_export_file is None:
        last_export_file = get_last_export_file()
    os.makedirs(os.path.dirname(last_export_file), exist_ok=True)
    data = {"manifest_path": manifest_path.replace("\\", "/")}
    with open(last_export_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# returns the manifest path Maya wrote last, or None when there is no last export
def read_last_export(last_export_file=None):
    if last_export_file is None:
        last_export_file = get_last_export_file()
    if not os.path.isfile(last_export_file):
        return None
    with open(last_export_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("manifest_path")

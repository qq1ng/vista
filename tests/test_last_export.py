from core import last_export


def test_read_without_a_file_gives_none(tmp_path):
    missing_file = str(tmp_path / "vista" / "last_export.json")
    assert last_export.read_last_export(missing_file) is None


def test_remember_then_read(tmp_path):
    last_export_file = str(tmp_path / "vista" / "last_export.json")
    last_export.remember_last_export("C:\\vista_out\\manifest.json", last_export_file)
    assert last_export.read_last_export(last_export_file) == "C:/vista_out/manifest.json"


def test_remember_replaces_the_older_path(tmp_path):
    last_export_file = str(tmp_path / "last_export.json")
    last_export.remember_last_export("C:/first/manifest.json", last_export_file)
    last_export.remember_last_export("C:/second/manifest.json", last_export_file)
    assert last_export.read_last_export(last_export_file) == "C:/second/manifest.json"


def test_last_export_file_sits_in_appdata(monkeypatch):
    monkeypatch.setenv("APPDATA", "C:/Users/test/AppData/Roaming")
    assert last_export.get_last_export_file() == "C:/Users/test/AppData/Roaming/vista/last_export.json"

import json
import os
import tempfile
import zipfile
from pathlib import Path

def validate_pack(folder, expected_type):
    folder = Path(folder)
    path = folder / "manifest.json"
    if not path.is_file():
        raise ValueError("В папке %s нет manifest.json." % folder.name)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise ValueError("Ошибка чтения %s/manifest.json: %s" % (folder.name, exc))
    if not isinstance(data, dict):
        raise ValueError("manifest.json должен быть JSON-объектом.")
    header, modules = data.get("header"), data.get("modules")
    if not isinstance(header, dict) or not isinstance(modules, list) or not modules:
        raise ValueError("%s: нужны разделы header и modules." % folder.name)
    for key in ("name", "uuid", "version"):
        if not header.get(key):
            raise ValueError("%s: отсутствует header.%s." % (folder.name, key))
    if expected_type == "BP":
        valid = any(isinstance(m, dict) and m.get("type") == "data" and m.get("uuid") for m in modules)
    else:
        valid = any(isinstance(m, dict) and m.get("type") == "resources" and m.get("uuid") for m in modules)
    if not valid:
        raise ValueError("%s: неверный тип модуля в manifest.json." % folder.name)

def _write_pack(folder, output_file):
    with zipfile.ZipFile(str(output_file), "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path(folder).rglob("*")):
            if path.is_file():
                archive.write(str(path), str(path.relative_to(folder)).replace(os.sep, "/"))

def export_mcaddon(project_folder, output_file):
    project = Path(project_folder)
    bp, rp = project / "BP", project / "RP"
    validate_pack(bp, "BP")
    validate_pack(rp, "RP")
    output_file = Path(output_file)
    if output_file.suffix.lower() != ".mcaddon":
        output_file = output_file.with_suffix(".mcaddon")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        bp_file = Path(temp) / "BehaviorPack.mcpack"
        rp_file = Path(temp) / "ResourcePack.mcpack"
        _write_pack(bp, bp_file)
        _write_pack(rp, rp_file)
        with zipfile.ZipFile(str(output_file), "w", zipfile.ZIP_DEFLATED) as addon:
            addon.write(str(bp_file), bp_file.name)
            addon.write(str(rp_file), rp_file.name)
    return output_file

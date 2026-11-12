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
    if not isinstance(header.get("version"), list) or len(header["version"]) != 3:
        raise ValueError("%s: header.version должен содержать три числа." % folder.name)
    expected = "data" if expected_type == "BP" else "resources"
    if not any(isinstance(m, dict) and m.get("type") == expected and m.get("uuid") for m in modules):
        raise ValueError("%s: не найден модуль типа %s с UUID." % (folder.name, expected))
    uuids = [header["uuid"]]
    for module in modules:
        if isinstance(module, dict) and module.get("uuid"):
            uuids.append(module["uuid"])
    if len(set(uuids)) != len(uuids):
        raise ValueError("%s: UUID в манифесте повторяются." % folder.name)
    for path in folder.rglob("*.json"):
        if path == folder / "manifest.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            raise ValueError("Некорректный JSON: %s (%s)" % (path.relative_to(folder), exc))
    return data

def _write_pack(folder, output_file):
    with zipfile.ZipFile(str(output_file), "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path(folder).rglob("*")):
            if path.is_file():
                relative = str(path.relative_to(folder)).replace(os.sep, "/")
                if relative.startswith("/") or ".." in Path(relative).parts:
                    raise ValueError("Недопустимый путь в пакете: " + relative)
                archive.write(str(path), relative)
    with zipfile.ZipFile(str(output_file), "r") as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError("Повреждённый файл внутри пакета: " + bad)
        if "manifest.json" not in archive.namelist():
            raise ValueError("В собранном пакете отсутствует manifest.json.")

def validate_mcaddon(addon_file):
    addon_file = Path(addon_file)
    if not addon_file.is_file() or addon_file.stat().st_size == 0:
        raise ValueError("Файл .mcaddon не создан или пуст.")
    with zipfile.ZipFile(str(addon_file), "r") as outer:
        bad = outer.testzip()
        if bad:
            raise ValueError("Повреждён архив .mcaddon: " + bad)
        packs = [n for n in outer.namelist() if n.lower().endswith(".mcpack")]
        if len(packs) != 2:
            raise ValueError("В .mcaddon должны находиться ровно два .mcpack (BP и RP).")
        seen_types = set()
        json_count = 0
        for pack_name in packs:
            raw = outer.read(pack_name)
            with zipfile.ZipFile(__import__("io").BytesIO(raw), "r") as pack:
                bad = pack.testzip()
                if bad:
                    raise ValueError("Повреждён пакет %s: %s" % (pack_name, bad))
                names = pack.namelist()
                if "manifest.json" not in names:
                    raise ValueError("В %s нет manifest.json." % pack_name)
                manifest = json.loads(pack.read("manifest.json").decode("utf-8-sig"))
                modules = manifest.get("modules", [])
                types = [m.get("type") for m in modules if isinstance(m, dict)]
                pack_type = "BP" if "data" in types else ("RP" if "resources" in types else None)
                if not pack_type or pack_type in seen_types:
                    raise ValueError("Не удалось определить тип или найден повтор пакета: " + pack_name)
                seen_types.add(pack_type)
                for name in names:
                    p = Path(name)
                    if p.is_absolute() or ".." in p.parts:
                        raise ValueError("Недопустимый путь в архиве: " + name)
                    if name.lower().endswith(".json"):
                        try:
                            json.loads(pack.read(name).decode("utf-8-sig"))
                            json_count += 1
                        except Exception as exc:
                            raise ValueError("Некорректный JSON внутри %s: %s" % (pack_name, name))
        if seen_types != {"BP", "RP"}:
            raise ValueError("В архиве должны быть и Behavior Pack, и Resource Pack.")
    return {"packs": ["Behavior Pack", "Resource Pack"], "json_files": json_count}

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
    validate_mcaddon(output_file)
    return output_file

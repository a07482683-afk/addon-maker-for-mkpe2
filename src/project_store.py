import json
from pathlib import Path
PROJECT_FILE = ".addonmaker.json"
def save_project_settings(project, settings=None):
    project = Path(project)
    data = {"format_version": 1, "name": project.name, "last_opened_tool": ""}
    existing = load_project_settings(project)
    data.update(existing)
    if settings: data.update(settings)
    target = project / PROJECT_FILE
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    return target
def load_project_settings(project):
    path = Path(project) / PROJECT_FILE
    if not path.is_file(): return {"format_version": 1, "name": Path(project).name, "last_opened_tool": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict): raise ValueError("Ожидался JSON-объект.")
        return data
    except Exception:
        return {"format_version": 1, "name": Path(project).name, "last_opened_tool": ""}
def validate_project_folder(project):
    project = Path(project)
    for pack in ("BP", "RP"):
        if not (project / pack / "manifest.json").is_file():
            raise ValueError("Не найдена папка %s/manifest.json. Выберите главную папку проекта." % pack)
    return project

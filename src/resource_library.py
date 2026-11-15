"""Persistent resource editing and texture library for the Addon Maker workspace."""
import json
import shutil
from pathlib import Path
from PySide2 import QtCore, QtGui, QtWidgets


class ResourceEditor(QtWidgets.QDialog):
    """Tabbed editor for a real project resource; saves the original file."""
    def __init__(self, path, project, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.project = Path(project)
        self.setWindowTitle("Редактор ресурса — " + self.path.name)
        self.resize(980, 740)
        root = QtWidgets.QVBoxLayout(self)
        head = QtWidgets.QLabel(str(self.path.relative_to(self.project)))
        head.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        root.addWidget(head)
        self.tabs = QtWidgets.QTabWidget()
        root.addWidget(self.tabs, 1)

        props = QtWidgets.QWidget()
        pl = QtWidgets.QVBoxLayout(props)
        self.summary = QtWidgets.QLabel()
        self.summary.setWordWrap(True)
        pl.addWidget(self.summary)
        self.form = QtWidgets.QFormLayout()
        pl.addLayout(self.form)
        pl.addStretch(1)
        self.tabs.addTab(props, "Свойства")

        raw = QtWidgets.QWidget()
        rl = QtWidgets.QVBoxLayout(raw)
        self.json_edit = QtWidgets.QPlainTextEdit()
        self.json_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        rl.addWidget(self.json_edit, 1)
        self.tabs.addTab(raw, "JSON")

        texture = QtWidgets.QWidget()
        tl = QtWidgets.QVBoxLayout(texture)
        self.texture_label = QtWidgets.QLabel("Текстуры, найденные в проекте")
        tl.addWidget(self.texture_label)
        self.texture_list = QtWidgets.QListWidget()
        tl.addWidget(self.texture_list, 1)
        self.tabs.addTab(texture, "Текстуры")

        row = QtWidgets.QHBoxLayout()
        self.status = QtWidgets.QLabel("Изменения сохраняются в исходный ресурс.")
        row.addWidget(self.status, 1)
        save = QtWidgets.QPushButton("Сохранить изменения")
        save.clicked.connect(self.save)
        close = QtWidgets.QPushButton("Закрыть")
        close.clicked.connect(self.close)
        row.addWidget(save)
        row.addWidget(close)
        root.addLayout(row)
        self._load()

    def _load(self):
        try:
            raw = self.path.read_text(encoding="utf-8-sig")
            data = json.loads(raw) if self.path.suffix.lower() == ".json" else {}
        except Exception as exc:
            raw, data = "", {}
            self.summary.setText("Не удалось прочитать JSON: " + str(exc))
        self.json_edit.setPlainText(raw)
        self.summary.setText("Тип: %s\nФайл: %s" % (self._kind(), self.path.name))
        self._make_fields(data)
        self._load_textures()

    def _kind(self):
        parts = [p.lower() for p in self.path.parts]
        for key, label in (("items","Предмет"),("blocks","Блок"),("entities","Сущность"),
                           ("biomes","Биом"),("recipes","Рецепт"),("features","Особенность"),
                           ("loot_tables","Таблица добычи"),("animations","Анимация")):
            if key in parts:
                return label
        return "JSON-ресурс"

    def _make_fields(self, data):
        while self.form.rowCount():
            self.form.removeRow(0)
        self.scalar_edits = {}
        if not isinstance(data, dict):
            return
        self._walk_fields(data, "")
        if not self.form.rowCount():
            self.form.addRow("Подсказка", QtWidgets.QLabel("Для любых полей доступна вкладка JSON."))

    def _walk_fields(self, value, prefix):
        if not isinstance(value, dict):
            return
        for key, item in value.items():
            path = (prefix + "." + key).strip(".")
            if isinstance(item, dict):
                self._walk_fields(item, path)
            elif isinstance(item, list):
                continue
            else:
                edit = QtWidgets.QLineEdit("" if item is None else str(item))
                edit.setToolTip("Путь в JSON: " + path)
                self.scalar_edits[path] = (edit, item)
                self.form.addRow(path, edit)

    def _load_textures(self):
        self.texture_list.clear()
        rp = self.project / "RP" / "textures"
        if not rp.is_dir():
            self.texture_label.setText("В проекте пока нет RP/textures.")
            return
        self.texture_label.setText("Текстуры проекта (PNG/JPG/BMP). Здесь можно открыть изображение для изменения.")
        for path in sorted(rp.rglob("*")):
            if path.is_file() and path.suffix.lower() in (".png",".jpg",".jpeg",".bmp"):
                item = QtWidgets.QListWidgetItem(str(path.relative_to(self.project)))
                item.setData(QtCore.Qt.UserRole, str(path))
                self.texture_list.addItem(item)

    def save(self):
        text = self.json_edit.toPlainText()
        if self.path.suffix.lower() == ".json":
            try:
                json.loads(text)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Некорректный JSON", "Исправь синтаксис перед сохранением.\n" + str(exc))
                self.tabs.setCurrentIndex(1)
                return
        try:
            if self.path.suffix.lower() == ".json":
                data = json.loads(text)
                for dotted, pair in getattr(self, "scalar_edits", {}).items():
                    edit, original = pair
                    target = data
                    parts = dotted.split(".")
                    for part in parts[:-1]:
                        if not isinstance(target, dict) or part not in target:
                            target = None
                            break
                        target = target[part]
                    if isinstance(target, dict) and parts[-1] in target:
                        value = edit.text()
                        if isinstance(original, bool):
                            value = value.strip().lower() in ("1", "true", "yes", "да")
                        elif isinstance(original, int) and not isinstance(original, bool):
                            try: value = int(value)
                            except ValueError: raise ValueError("Поле %s должно быть целым числом." % dotted)
                        elif isinstance(original, float):
                            try: value = float(value.replace(",", "."))
                            except ValueError: raise ValueError("Поле %s должно быть числом." % dotted)
                        target[parts[-1]] = value
                text = json.dumps(data, indent=2, ensure_ascii=False)
            self.path.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
            self.status.setText("Сохранено: " + self.path.name)
            self._load()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка сохранения", str(exc))


class TextureLibrary(QtWidgets.QDialog):
    """Central project texture library for item, block, entity, biome and UI assets."""
    FOLDERS = {
        "Предметы": "items", "Блоки": "blocks", "Сущности": "entity",
        "Биомы / окружение": "environment", "Иконки и интерфейс": "ui",
        "Прочее": "misc"
    }
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = Path(project)
        self.setWindowTitle("Библиотека текстур проекта")
        self.resize(900, 650)
        root = QtWidgets.QVBoxLayout(self)
        row = QtWidgets.QHBoxLayout()
        self.category = QtWidgets.QComboBox()
        self.category.addItems(list(self.FOLDERS))
        row.addWidget(QtWidgets.QLabel("Категория:"))
        row.addWidget(self.category)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Поиск текстуры по имени…")
        row.addWidget(self.search, 1)
        root.addLayout(row)
        body = QtWidgets.QHBoxLayout()
        self.files = QtWidgets.QListWidget()
        self.files.currentItemChanged.connect(self.preview)
        body.addWidget(self.files, 1)
        self.image = QtWidgets.QLabel("Предпросмотр")
        self.image.setAlignment(QtCore.Qt.AlignCenter)
        self.image.setMinimumSize(360, 360)
        self.image.setStyleSheet("background:#17191d;border:1px solid #444;")
        body.addWidget(self.image, 2)
        root.addLayout(body, 1)
        buttons = QtWidgets.QHBoxLayout()
        for label, cb in (("Импортировать изображения…", self.import_images),
                          ("Открыть в редакторе", self.edit_image),
                          ("Удалить файл", self.delete_image),
                          ("Обновить", self.refresh)):
            b = QtWidgets.QPushButton(label); b.clicked.connect(cb); buttons.addWidget(b)
        root.addLayout(buttons)
        self.search.textChanged.connect(self.refresh)
        self.category.currentTextChanged.connect(self.refresh)
        self.refresh()

    def folder(self):
        return self.project / "RP" / "textures" / self.FOLDERS[self.category.currentText()]

    def refresh(self, *_):
        self.files.clear()
        root = self.folder()
        if root.is_dir():
            for path in sorted(root.rglob("*")):
                if path.is_file() and path.suffix.lower() in (".png",".jpg",".jpeg",".bmp"):
                    if self.search.text().lower() in path.name.lower():
                        item = QtWidgets.QListWidgetItem(str(path.relative_to(root)))
                        item.setData(QtCore.Qt.UserRole, str(path))
                        self.files.addItem(item)

    def current_path(self):
        item = self.files.currentItem()
        return Path(item.data(QtCore.Qt.UserRole)) if item else None

    def preview(self, current, previous=None):
        path = self.current_path()
        if not path:
            self.image.setText("Предпросмотр")
            self.image.setPixmap(QtGui.QPixmap())
            return
        pix = QtGui.QPixmap(str(path))
        if pix.isNull():
            self.image.setText("Не удалось открыть изображение")
        else:
            self.image.setPixmap(pix.scaled(self.image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.preview(self.files.currentItem())

    def import_images(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Импортировать текстуры", "", "Изображения (*.png *.jpg *.jpeg *.bmp)")
        if not files:
            return
        target = self.folder()
        target.mkdir(parents=True, exist_ok=True)
        errors = []
        for src in files:
            source = Path(src)
            dest = target / source.name
            if dest.exists():
                answer = QtWidgets.QMessageBox.question(self, "Файл существует", "Заменить %s?" % dest.name,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if answer != QtWidgets.QMessageBox.Yes:
                    continue
            try:
                shutil.copy2(str(source), str(dest))
            except Exception as exc:
                errors.append("%s: %s" % (source.name, exc))
        self.refresh()
        if errors:
            QtWidgets.QMessageBox.warning(self, "Некоторые файлы не импортированы", "\n".join(errors))

    def edit_image(self):
        path = self.current_path()
        if not path:
            return
        try:
            from editors import TextureEditor
            TextureEditor(self, str(self.project), str(path)).exec_()
            self.refresh()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка редактора", str(exc))

    def delete_image(self):
        path = self.current_path()
        if not path:
            return
        if QtWidgets.QMessageBox.question(self, "Удалить текстуру", "Удалить файл %s?" % path.name,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return
        try:
            path.unlink()
            self.refresh()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка удаления", str(exc))


def compatibility_report(project):
    """Structural checks plus conservative feature gates for the selected Bedrock target."""
    project = Path(project)
    errors, warnings, checked = [], [], 0
    settings_path = project / ".addonmaker.json"
    target_version = "1.20.0"
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))
            target_version = settings.get("target_version", target_version)
        except Exception:
            warnings.append("Не удалось прочитать .addonmaker.json; версия проекта принята как 1.20.0.")
    try:
        version_tuple = tuple(int(x) for x in str(target_version).split(".")[:3])
    except Exception:
        version_tuple = (1, 20, 0)
    uuids = {}
    for pack_name in ("BP", "RP"):
        pack = project / pack_name
        manifest = pack / "manifest.json"
        if not manifest.is_file():
            errors.append("%s: отсутствует manifest.json" % pack_name)
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8-sig"))
            header = data.get("header", {})
            min_engine = header.get("min_engine_version", [])
            if target_version == "1.7.0" and min_engine != [1, 7, 0]:
                errors.append("%s/manifest.json: min_engine_version должен быть [1, 7, 0] для профиля MCPE 1.7.0." % pack_name)
            for uid in [header.get("uuid")] + [m.get("uuid") for m in data.get("modules", []) if isinstance(m, dict)]:
                if uid:
                    if uid in uuids:
                        errors.append("Повтор UUID %s (%s и %s)" % (uid, uuids[uid], pack_name))
                    uuids[uid] = pack_name
        except Exception as exc:
            errors.append("%s/manifest.json: %s" % (pack_name, exc))
        for path in pack.rglob("*.json"):
            checked += 1
            try:
                obj = json.loads(path.read_text(encoding="utf-8-sig"))
                if not isinstance(obj, (dict, list)):
                    warnings.append("%s: JSON верхнего уровня не объект/список" % path.relative_to(project))
                if isinstance(obj, dict) and "format_version" not in obj and path.name != "manifest.json":
                    warnings.append("%s: отсутствует format_version" % path.relative_to(project))
                if version_tuple <= (1, 7, 0) and isinstance(obj, dict):
                    rel = str(path.relative_to(project)).replace("\\", "/").lower()
                    modern = []
                    if "minecraft:item" in obj:
                        modern.append("современный формат пользовательского предмета")
                    if "minecraft:block" in obj:
                        modern.append("современный формат пользовательского блока")
                    if "minecraft:biome" in obj:
                        modern.append("современный формат пользовательского биома")
                    if rel.startswith("bp/items/") or rel.startswith("bp/blocks/"):
                        modern.append("современная папка пользовательских предметов/блоков")
                    if modern:
                        errors.append("%s: %s не совместимы с MCPE 1.7.0." %
                                      (path.relative_to(project), ", ".join(sorted(set(modern)))))
            except Exception as exc:
                errors.append("%s: некорректный JSON (%s)" % (path.relative_to(project), exc))
    if not (project / "RP" / "textures").exists():
        warnings.append("В RP нет папки textures — проверь, нужны ли проекту изображения.")
    if target_version != "1.7.0" and not (project / "BP" / "items").exists():
        warnings.append("Папка BP/items отсутствует (это нормально, если предметов нет).")
    return {"errors": errors, "warnings": warnings, "json_checked": checked,
            "target_version": target_version}

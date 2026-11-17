"""Blender-inspired project workspace for Addon Maker.
The project tree is the source of truth: every generated/imported file remains visible
and can be reopened for editing.
"""
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from PySide2 import QtCore, QtWidgets
from main import MainWindow, create_project
from project_store import validate_project_folder
from mcaddon_export import export_mcaddon, export_mcpe170_mcaddon, validate_mcaddon


class JsonEditor(QtWidgets.QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.setWindowTitle("Редактор файла — " + self.path.name)
        self.resize(900, 700)
        layout = QtWidgets.QVBoxLayout(self)
        self.info = QtWidgets.QLabel(str(self.path))
        self.info.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.info)
        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        try:
            self.editor.setPlainText(self.path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            self.editor.setPlainText("")
            QtWidgets.QMessageBox.critical(self, "Не удалось открыть", str(exc))
        layout.addWidget(self.editor, 1)
        row = QtWidgets.QHBoxLayout()
        self.status = QtWidgets.QLabel("Изменения сохраняются в исходный файл.")
        row.addWidget(self.status, 1)
        save = QtWidgets.QPushButton("Сохранить")
        save.clicked.connect(self.save)
        close = QtWidgets.QPushButton("Закрыть")
        close.clicked.connect(self.close)
        row.addWidget(save)
        row.addWidget(close)
        layout.addLayout(row)

    def save(self):
        text = self.editor.toPlainText()
        if self.path.suffix.lower() == ".json":
            try:
                json.loads(text)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "JSON с ошибкой", "Исправь JSON перед сохранением.\\n" + str(exc))
                return
        try:
            self.path.write_text(text + ("\\n" if not text.endswith("\\n") else ""), encoding="utf-8")
            self.status.setText("Сохранено: " + self.path.name)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка сохранения", str(exc))


class WorkspaceWindow(MainWindow):
    """Single-window editor with persistent project browser and editable resources."""

    def build_ui(self):
        self.setWindowTitle("Addon Maker • Рабочая среда")
        self.resize(1280, 820)
        self.setMinimumSize(980, 650)
        self.setStyleSheet("""
        QMainWindow, QWidget { background:#202226; color:#e6e6e6; font-family:Segoe UI,Arial; font-size:10pt; }
        QMenuBar, QMenu, QToolBar { background:#292c31; color:#eee; }
        QDockWidget { color:#eee; font-weight:600; }
        QDockWidget::title { background:#30343b; padding:7px; }
        QTreeWidget, QPlainTextEdit, QListWidget { background:#17191d; color:#e7e7e7; border:1px solid #3b4048; }
        QGroupBox { border:1px solid #424750; border-radius:5px; margin-top:9px; padding:8px; }
        QGroupBox::title { subcontrol-origin:margin; left:9px; padding:0 4px; }
        QPushButton { background:#383e48; border:1px solid #505866; border-radius:4px; padding:7px 10px; }
        QPushButton:hover { background:#4b5666; }
        QPushButton#Primary { background:#526eaa; border-color:#6686c8; }
        QLineEdit { background:#17191d; border:1px solid #454b55; padding:6px; }
        """)
        self.setDockNestingEnabled(True)
        self._build_menus()
        self._build_toolbar()

        self.tree_search = QtWidgets.QLineEdit()
        self.tree_search.setPlaceholderText("Поиск ресурса по имени…")
        self.tree_search.textChanged.connect(self._apply_tree_filter)
        self.tree_filter = QtWidgets.QComboBox()
        self.tree_filter.addItems(["Все типы", "JSON", "PNG", "Изображение", "3D-модель OBJ", "3D-модель FBX", "Папка"])
        self.tree_filter.currentTextChanged.connect(self._apply_tree_filter)
        tree_panel = QtWidgets.QWidget()
        tree_layout = QtWidgets.QVBoxLayout(tree_panel)
        tree_layout.setContentsMargins(4,4,4,4)
        tree_layout.addWidget(self.tree_search)
        tree_layout.addWidget(self.tree_filter)
        self.project_tree = QtWidgets.QTreeWidget()
        self.project_tree.setHeaderLabels(["Проект / файлы", "Тип"])
        self.project_tree.setColumnWidth(0, 260)
        self.project_tree.itemDoubleClicked.connect(self._open_tree_item)
        self.project_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.project_tree.customContextMenuRequested.connect(self._tree_menu)
        dock = QtWidgets.QDockWidget("ПРОЕКТ — все ресурсы всегда здесь", self)
        dock.setObjectName("ProjectBrowser")
        tree_layout.addWidget(self.project_tree)
        dock.setWidget(tree_panel)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)

        center = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(center)
        layout.setContentsMargins(20, 16, 20, 16)
        heading = QtWidgets.QLabel("Рабочая область")
        heading.setStyleSheet("font-size:20pt;font-weight:700;")
        layout.addWidget(heading)
        self.project_label = QtWidgets.QLabel("Создай проект или открой существующий. Все созданные файлы появятся в дереве слева.")
        self.project_label.setWordWrap(True)
        layout.addWidget(self.project_label)
        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.work_tabs = QtWidgets.QTabWidget()
        self.work_tabs.setDocumentMode(True)
        welcome = QtWidgets.QWidget()
        wl = QtWidgets.QVBoxLayout(welcome)
        wl.addWidget(QtWidgets.QLabel("Выбери ресурс в дереве проекта или создай новый."))
        wl.addWidget(QtWidgets.QLabel("Двойной щелчок по JSON открывает его для редактирования. PNG можно открыть в редакторе текстур, OBJ — в просмотрщике моделей."))
        wl.addStretch(1)
        self.work_tabs.addTab(welcome, "Главная")
        split.addWidget(self.work_tabs)
        properties = QtWidgets.QFrame()
        properties.setMinimumWidth(220)
        pl = QtWidgets.QVBoxLayout(properties)
        pl.addWidget(QtWidgets.QLabel("СВОЙСТВА ПРОЕКТА"))
        self.property_text = QtWidgets.QLabel("Выбери файл слева, чтобы открыть или изменить его.")
        self.property_text.setWordWrap(True)
        pl.addWidget(self.property_text)
        pl.addStretch(1)
        split.addWidget(properties)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)
        self.setCentralWidget(center)
        self.statusBar().showMessage("Готово. Создай проект или открой существующий.")
        if self.project_path:
            self.refresh_project_tree()

    def _build_menus(self):
        file_menu = self.menuBar().addMenu("Файл")
        for label, callback in (("Новый проект", self.new_project), ("Открыть проект…", self.open_project),
                                ("Импортировать .mcaddon/.mcpack…", self.import_addon),
                                ("Экспортировать .mcaddon…", self.export_project),
                                ("Обновить дерево проекта", self.refresh_project_tree)):
            action = file_menu.addAction(label)
            action.triggered.connect(callback)
        file_menu.addSeparator()
        file_menu.addAction("Выход", self.close)
        create_menu = self.menuBar().addMenu("Создать")
        for label, key in (("Предмет", "item"), ("Блок", "block"), ("Броня", "armor"),
                           ("Текстуру", "texture"), ("Библиотека текстур", "texture_library"), ("3D-модель", "model"), ("События", "logic"),
                           ("Подключить PNG", "registry"), ("MCPE 1.7.0 — ModPE Studio", "modpe")):
            action = create_menu.addAction(label)
            action.triggered.connect(lambda checked=False, k=key: self.open_tool(k))
        window_menu = self.menuBar().addMenu("Окна")
        window_menu.addAction("Показать дерево проекта", lambda: self.findChild(QtWidgets.QDockWidget, "ProjectBrowser").show())

    def _build_toolbar(self):
        bar = self.addToolBar("Основные действия")
        bar.setMovable(False)
        actions = [("Новый", self.new_project), ("Открыть", self.open_project),
                   ("Импорт аддона", self.import_addon), ("Экспорт .mcaddon", self.export_project),
                   ("Обновить", self.refresh_project_tree)]
        for label, callback in actions:
            action = bar.addAction(label)
            action.triggered.connect(callback)

    def set_project(self, path):
        super().set_project(path)
        self.refresh_project_tree()

    def set_project(self, path):
        super().set_project(path)
        version = getattr(self, "project_settings", {}).get("target_version")
        if not version:
            # Infer a useful target from existing imported packs when no project metadata exists.
            try:
                manifest_path = Path(path) / "BP" / "manifest.json"
                data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
                version = ".".join(str(x) for x in data.get("header", {}).get("min_engine_version", [1, 20, 0]))
            except Exception:
                version = "unknown"
            from project_store import save_project_settings
            self.project_settings["target_version"] = version
            save_project_settings(path, {"target_version": version})
        self.project_label.setText("ПРОЕКТ: %s    •    ЦЕЛЕВАЯ ВЕРСИЯ: %s" % (Path(path).name, version))
        self.statusBar().showMessage("Открыт проект для Minecraft %s" % version)
        self.refresh_project_tree()

    def refresh_project_tree(self):
        if not hasattr(self, "project_tree"):
            return
        self.project_tree.clear()
        if not self.project_path or not Path(self.project_path).is_dir():
            return
        root_path = Path(self.project_path)
        root = QtWidgets.QTreeWidgetItem([root_path.name, "Проект"])
        root.setData(0, QtCore.Qt.UserRole, str(root_path))
        self.project_tree.addTopLevelItem(root)
        for folder_name in ("BP", "RP", "Examples", "TextureProjects"):
            folder = root_path / folder_name
            if not folder.is_dir():
                continue
            node = QtWidgets.QTreeWidgetItem([folder_name, "Папка"])
            node.setData(0, QtCore.Qt.UserRole, str(folder))
            root.addChild(node)
            self._add_folder_items(node, folder)
            node.setExpanded(True)
        for path in sorted(root_path.iterdir()):
            if path.is_file() and path.name not in (".addonmaker.json",):
                node = QtWidgets.QTreeWidgetItem([path.name, self._file_kind(path)])
                node.setData(0, QtCore.Qt.UserRole, str(path))
                root.addChild(node)
        root.setExpanded(True)
        self.project_tree.resizeColumnToContents(0)
        self._apply_tree_filter()

    def _add_folder_items(self, parent, folder):
        try:
            children = sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return
        for path in children:
            kind = "Папка" if path.is_dir() else self._file_kind(path)
            node = QtWidgets.QTreeWidgetItem([path.name, kind])
            node.setData(0, QtCore.Qt.UserRole, str(path))
            parent.addChild(node)
            if path.is_dir():
                self._add_folder_items(node, path)

    @staticmethod
    def _file_kind(path):
        ext = path.suffix.lower()
        return {".json":"JSON", ".png":"PNG", ".jpg":"Изображение", ".jpeg":"Изображение",
                ".obj":"3D-модель OBJ", ".fbx":"3D-модель FBX", ".mcaddon":"Аддон",
                ".mcpack":"Пакет", ".tstudio":"Проект текстуры", ".txt":"Текст"}.get(ext, "Файл")

    def _apply_tree_filter(self, *_):
        if not hasattr(self, "project_tree"):
            return
        query = self.tree_search.text().lower().strip()
        kind = self.tree_filter.currentText()
        def visit(item):
            child_visible = False
            for i in range(item.childCount()):
                if visit(item.child(i)):
                    child_visible = True
            name_match = query in item.text(0).lower()
            type_match = kind == "Все типы" or item.text(1) == kind or item.text(1) == "Папка"
            visible = (name_match and type_match) or child_visible
            item.setHidden(not visible)
            return visible
        for i in range(self.project_tree.topLevelItemCount()):
            visit(self.project_tree.topLevelItem(i))

    def _open_tree_item(self, item, column):
        raw = item.data(0, QtCore.Qt.UserRole)
        if not raw:
            return
        path = Path(raw)
        if path.is_dir():
            item.setExpanded(not item.isExpanded())
            return
        if path.suffix.lower() in (".json", ".txt", ".lang", ".material"):
            from resource_library import ResourceEditor
            editor = ResourceEditor(path, self.project_path, self)
            editor.exec_()
            self.refresh_project_tree()
            return
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"):
            if self.project_path:
                from editors import TextureEditor
                TextureEditor(self, str(self.project_path), str(path)).exec_()
                self.refresh_project_tree()
            return
        if path.suffix.lower() in (".obj", ".fbx"):
            from model_editor import ModelWorkspace
            ModelWorkspace(self, str(self.project_path) if self.project_path else None).exec_()
            return
        if path.suffix.lower() == ".tstudio":
            QtWidgets.QMessageBox.information(self, "Проект текстуры", "Открой редактор текстур и выбери «Открыть проект», затем укажи этот .tstudio файл.")

    def _tree_menu(self, pos):
        item = self.project_tree.itemAt(pos)
        if not item:
            return
        raw = item.data(0, QtCore.Qt.UserRole)
        if not raw:
            return
        path = Path(raw)
        menu = QtWidgets.QMenu(self)
        if path.is_file() and path.suffix.lower() in (".json", ".txt", ".lang"):
            menu.addAction("Редактировать", lambda: self._open_tree_item(item, 0))
        if path.is_dir():
            menu.addAction("Открыть папку в проводнике", lambda: QtCore.QProcess.startDetached("explorer", [str(path)]))
        menu.exec_(self.project_tree.viewport().mapToGlobal(pos))

    def open_tool(self, key):
        if key == "modpe":
            if not self.ensure_project():
                return
            from modpe_editor import ModPEStudio
            ModPEStudio(self.project_path, self).exec_()
            self.refresh_project_tree()
            return
        if key == "texture_library":
            if not self.ensure_project():
                return
            from resource_library import TextureLibrary
            TextureLibrary(self.project_path, self).exec_()
            self.refresh_project_tree()
            return
        if key not in ("model", "texture", "logic") and not self.ensure_project():
            return
        if key in ("model", "texture", "logic") and self.project_path is None:
            QtWidgets.QMessageBox.information(self, "Сначала проект", "Создай или открой проект, чтобы новые ресурсы сохранялись в нём.")
            return
        super().open_tool(key)
        self.refresh_project_tree()

    def import_addon(self):
        source, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Импортировать аддон Minecraft", "", "Minecraft Add-ons (*.mcaddon *.mcpack)")
        if not source:
            return
        source = Path(source)
        name = source.stem + " (импорт)"
        location = QtWidgets.QFileDialog.getExistingDirectory(self, "Куда создать проект для импортированного аддона", str(Path.home() / "Documents"))
        if not location:
            return
        safe_name = "".join(ch for ch in name if ch.isalnum() or ch in " -_").strip()
        target = Path(location) / safe_name
        if target.exists():
            QtWidgets.QMessageBox.warning(self, "Папка уже существует", "Выбери другое место или переименуй существующую папку.")
            return
        try:
            target.mkdir(parents=True)
            bp, rp = target / "BP", target / "RP"
            bp.mkdir(); rp.mkdir()
            packs = []
            with zipfile.ZipFile(str(source), "r") as archive:
                for member in archive.namelist():
                    if member.lower().endswith(".mcpack"):
                        packs.append((member, archive.read(member)))
                if not packs and source.suffix.lower() == ".mcpack":
                    packs.append((source.name, source.read_bytes()))
            if not packs:
                raise ValueError("В архиве не найдены .mcpack пакеты.")
            import io
            imported = set()
            for pack_name, raw in packs:
                with zipfile.ZipFile(io.BytesIO(raw), "r") as pack:
                    names = pack.namelist()
                    if "manifest.json" not in names:
                        continue
                    manifest = json.loads(pack.read("manifest.json").decode("utf-8-sig"))
                    types = [m.get("type") for m in manifest.get("modules", []) if isinstance(m, dict)]
                    kind = "BP" if "data" in types else ("RP" if "resources" in types else None)
                    if not kind:
                        continue
                    if kind in imported:
                        raise ValueError("В аддоне несколько пакетов одного типа. Импорт остановлен, чтобы не перезаписать данные.")
                    imported.add(kind)
                    dest = bp if kind == "BP" else rp
                    for member in names:
                        p = Path(member)
                        if p.is_absolute() or ".." in p.parts or not p.parts:
                            raise ValueError("Небезопасный путь в архиве: " + member)
                        if member.endswith("/"):
                            continue
                        out = dest.joinpath(*p.parts)
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(pack.read(member))
            if not imported:
                raise ValueError("Не удалось определить Behavior Pack / Resource Pack по manifest.json.")
            if "BP" not in imported:
                raise ValueError("В файле нет Behavior Pack. Импортируй .mcaddon, содержащий BP и RP.")
            if "RP" not in imported:
                QtWidgets.QMessageBox.warning(self, "Импорт частичный", "Resource Pack не найден. Создан проект только с Behavior Pack; некоторые ресурсы могут отсутствовать.")
            self.set_project(target)
            QtWidgets.QMessageBox.information(self, "Импорт завершён", "Файлы аддона распакованы в проект. JSON можно открывать двойным щелчком в дереве слева. Неизвестные или неподдерживаемые игровые компоненты могут потребовать ручной правки.")
        except Exception as exc:
            shutil.rmtree(str(target), ignore_errors=True)
            QtWidgets.QMessageBox.critical(self, "Ошибка импорта", str(exc))

    def export_project(self):
        if not self.ensure_project():
            return
        suggested = str(Path(self.project_path) / (Path(self.project_path).name + ".mcaddon"))
        target, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Экспортировать аддон", suggested, "Minecraft Add-on (*.mcaddon)")
        if not target:
            return
        target_version = getattr(self, "project_settings", {}).get("target_version", "1.20.0")
        if target_version == "1.7.0":
            try:
                result = export_mcpe170_mcaddon(self.project_path, target)
                report = validate_mcaddon(result)
                with zipfile.ZipFile(str(result), "r") as archive:
                    legacy_scripts = sum(1 for n in archive.namelist()
                                         if n.startswith("LegacyModPE/scripts/") and n.endswith(".js"))
                    legacy_textures = sum(1 for n in archive.namelist()
                                          if n.startswith("LegacyModPE/textures/"))
                QtWidgets.QMessageBox.information(
                    self, "Экспорт MCPE 1.7.0 завершён",
                    "Создан файл .mcaddon и проверена структура архива.\\n" + str(result) +
                    "\\n\\nВнутри: Behavior Pack + Resource Pack" +
                    "\\nModPE-скриптов: " + str(legacy_scripts) +
                    "\\nФайлов LegacyTextures: " + str(legacy_textures) +
                    "\\n\\nВАЖНО: MCPE 1.7.0 не запускает ModPE JavaScript из .mcaddon. "
                    "Скрипты и текстуры включены внутрь архива для переноса; "
                    "для запуска .js нужен совместимый BlockLauncher."
                )
                self.statusBar().showMessage("Экспорт MCPE 1.7.0 завершён: " + str(result))
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Не удалось экспортировать", str(exc))
            self.refresh_project_tree()
            return
        from resource_library import compatibility_report
        preflight = compatibility_report(self.project_path)
        if preflight["errors"]:
            QtWidgets.QMessageBox.critical(self, "Проверка проекта не пройдена",
                "Найдено ошибок: %d\n\n" % len(preflight["errors"]) + "\n".join(preflight["errors"][:30]))
            return
        if preflight["warnings"]:
            answer = QtWidgets.QMessageBox.warning(self, "Есть предупреждения",
                "JSON проверено: %d\nПредупреждений: %d\n\n" % (preflight["json_checked"], len(preflight["warnings"])) +
                "\n".join(preflight["warnings"][:20]) + "\n\nПродолжить экспорт?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return
        try:
            result = export_mcaddon(self.project_path, target)
            report = validate_mcaddon(result)
            QtWidgets.QMessageBox.information(self, "Экспорт завершён",
                "Создан .mcaddon и пройдена структурная проверка архива.\\n" + str(result) +
                "\\nПакеты: " + ", ".join(report["packs"]) +
                "\\nJSON проверено: " + str(report["json_files"]) +
                "\\nИмпорт в саму игру нужно проверить отдельно.")
            self.statusBar().showMessage("Экспорт завершён: " + str(result))
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка экспорта", str(exc))
        self.refresh_project_tree()

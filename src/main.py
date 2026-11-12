import sys
import uuid
from pathlib import Path
from PySide2 import QtWidgets
from editors import TextureEditor, LogicWorkspace
from content_editors import ItemEditor, BlockEditor, ArmorEditor, TextureRegistryEditor
from model_editor import ModelWorkspace
from mcaddon_export import export_mcaddon, validate_mcaddon
from project_store import save_project_settings, load_project_settings, validate_project_folder
from examples import create_learning_examples

APP_NAME = "Addon Maker для MCPE"
APP_VERSION = "0.7.0"

def write_json(path, data):
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")

def manifest(name, description, pack_type):
    return {
        "format_version": 2,
        "header": {"name": name, "description": description, "uuid": str(uuid.uuid4()),
                   "version": [1, 0, 0], "min_engine_version": [1, 20, 0]},
        "modules": [{"type": "data" if pack_type == "BP" else "resources",
                     "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}]
    }

def create_project(location, name, description):
    safe = "".join(c for c in name if c.isalnum() or c in " -_").strip()
    if not safe:
        raise ValueError("Введите название проекта.")
    root = Path(location).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    project = root / safe
    if project.exists():
        raise FileExistsError("Такая папка уже существует. Выберите другое имя или место.")
    bp, rp = project / "BP", project / "RP"
    bp.mkdir(parents=True)
    rp.mkdir(parents=True)
    write_json(bp / "manifest.json", manifest(safe + " BP", description, "BP"))
    write_json(rp / "manifest.json", manifest(safe + " RP", description, "RP"))
    (project / "README.txt").write_text(safe + chr(10) + "BP — поведение и предметы." + chr(10) + "RP — текстуры и ресурсы." + chr(10), encoding="utf-8")
    create_learning_examples(project)
    save_project_settings(project)
    return project

class ProjectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать проект")
        self.setMinimumWidth(500)
        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel("Напишите название. Программа сама создаст нужные папки.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QtWidgets.QFormLayout()
        self.name = QtWidgets.QLineEdit("Мой первый аддон")
        self.description = QtWidgets.QLineEdit("Аддон для Minecraft Bedrock")
        self.location = QtWidgets.QLineEdit(str(Path.home() / "Documents" / "MCPE Addons"))
        browse = QtWidgets.QPushButton("Обзор…")
        browse.clicked.connect(self.browse)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.location, 1)
        row.addWidget(browse)
        form.addRow("Название:", self.name)
        form.addRow("Описание:", self.description)
        form.addRow("Сохранить в:", row)
        layout.addLayout(form)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText("Создать")
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def browse(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите место")
        if folder:
            self.location.setText(folder)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.project_path = None
        self.settings = QtWidgets.QSettings("AddonMaker", "MCPE")
        self.setWindowTitle(APP_NAME + " • " + APP_VERSION)
        self.resize(1040, 720)
        self.setMinimumSize(850, 600)
        self.setStyleSheet("""
        QWidget { background:#17191f; color:#e7eaf0; font-family:Segoe UI,Arial; font-size:11pt; }
        QFrame#Card { background:#222631; border:1px solid #343b4b; border-radius:12px; }
        QLabel#Title { font-size:25pt; font-weight:700; }
        QLabel#Muted { color:#aab2c2; }
        QPushButton { background:#343d50; border:1px solid #4b5870; border-radius:8px; padding:12px; }
        QPushButton:hover { background:#46536b; }
        QPushButton#Primary { background:#667af5; border:0; color:white; font-weight:700; }
        """)
        self.build_ui()
        recent = self.settings.value("recent_project", "")
        if recent and Path(recent).is_dir():
            try:
                self.set_project(validate_project_folder(recent))
            except Exception:
                pass

    def build_ui(self):
        root = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(26, 22, 26, 20)
        layout.setSpacing(14)
        title = QtWidgets.QLabel("Создаём аддон для Minecraft")
        title.setObjectName("Title")
        layout.addWidget(title)
        subtitle = QtWidgets.QLabel("Просто выполняйте шаги по порядку. Программирование не требуется.")
        subtitle.setObjectName("Muted")
        layout.addWidget(subtitle)

        project_card = QtWidgets.QFrame()
        project_card.setObjectName("Card")
        pc = QtWidgets.QVBoxLayout(project_card)
        self.project_label = QtWidgets.QLabel("ШАГ 1. Сначала создайте проект или откройте существующий.")
        self.project_label.setWordWrap(True)
        pc.addWidget(self.project_label)
        row = QtWidgets.QHBoxLayout()
        create = QtWidgets.QPushButton("＋ Создать проект")
        create.setObjectName("Primary")
        create.clicked.connect(self.new_project)
        open_btn = QtWidgets.QPushButton("Открыть проект…")
        open_btn.clicked.connect(self.open_project)
        row.addWidget(create)
        row.addWidget(open_btn)
        row.addStretch(1)
        pc.addLayout(row)
        layout.addWidget(project_card)

        label = QtWidgets.QLabel("ШАГ 2. Что хотите добавить?")
        label.setStyleSheet("font-size:15pt;font-weight:700;")
        layout.addWidget(label)
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        cards = [
            ("Предмет", "Создать предмет для игры", "item"),
            ("Блок", "Создать собственный блок", "block"),
            ("Броня", "Создать шлем, нагрудник и другое", "armor"),
            ("Текстура", "Нарисовать картинку", "texture"),
            ("3D-модель", "Открыть и посмотреть модель", "model"),
            ("События", "Настроить действия и код", "logic"),
            ("Добавить PNG в игру", "Подключить текстуру к проекту", "registry"),
            ("Учебные примеры", "Изучить предметы, блоки и биомы", "examples"),
        ]
        for i, (name, description, key) in enumerate(cards):
            card = QtWidgets.QFrame()
            card.setObjectName("Card")
            box = QtWidgets.QVBoxLayout(card)
            heading = QtWidgets.QLabel(name)
            heading.setStyleSheet("font-size:14pt;font-weight:700;")
            desc = QtWidgets.QLabel(description)
            desc.setObjectName("Muted")
            desc.setWordWrap(True)
            button = QtWidgets.QPushButton("Открыть")
            button.clicked.connect(lambda checked=False, k=key: self.open_tool(k))
            box.addWidget(heading)
            box.addWidget(desc)
            box.addStretch(1)
            box.addWidget(button)
            grid.addWidget(card, i // 3, i % 3)
        layout.addLayout(grid, 1)

        export_card = QtWidgets.QFrame()
        export_card.setObjectName("Card")
        erow = QtWidgets.QHBoxLayout(export_card)
        text_box = QtWidgets.QVBoxLayout()
        export_title = QtWidgets.QLabel("ШАГ 3. Собрать готовый аддон")
        export_title.setStyleSheet("font-size:14pt;font-weight:700;")
        export_desc = QtWidgets.QLabel("Программа упакует BP и RP в файл .mcaddon для Minecraft.")
        export_desc.setObjectName("Muted")
        export_desc.setWordWrap(True)
        text_box.addWidget(export_title)
        text_box.addWidget(export_desc)
        erow.addLayout(text_box, 1)
        export_btn = QtWidgets.QPushButton("Экспортировать .mcaddon")
        export_btn.setObjectName("Primary")
        export_btn.clicked.connect(self.export_project)
        erow.addWidget(export_btn)
        layout.addWidget(export_card)
        self.setCentralWidget(root)
        self.statusBar().showMessage("Сначала создайте или откройте проект.")

    def set_project(self, path):
        self.project_path = validate_project_folder(path)
        self.project_settings = load_project_settings(self.project_path)
        self.settings.setValue("recent_project", str(self.project_path))
        save_project_settings(self.project_path, self.project_settings)
        self.project_label.setText("ТЕКУЩИЙ ПРОЕКТ: " + str(self.project_path))
        self.statusBar().showMessage("Проект открыт. Выбирайте нужный редактор.")

    def new_project(self):
        dialog = ProjectDialog(self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        try:
            project = create_project(dialog.location.text().strip(), dialog.name.text().strip(),
                                     dialog.description.text().strip() or dialog.name.text().strip())
            self.set_project(project)
            QtWidgets.QMessageBox.information(self, "Готово!", "Проект создан. Теперь выберите, что добавить.")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка создания", str(exc))

    def open_project(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите главную папку проекта")
        if not folder:
            return
        project = Path(folder)
        if not (project / "BP" / "manifest.json").is_file() or not (project / "RP" / "manifest.json").is_file():
            QtWidgets.QMessageBox.warning(self, "Не та папка", "Внутри выбранной папки должны быть BP и RP. Выберите главную папку проекта.")
            return
        self.set_project(project)

    def ensure_project(self):
        if self.project_path and (self.project_path / "BP").is_dir() and (self.project_path / "RP").is_dir():
            return True
        QtWidgets.QMessageBox.information(self, "Нужен проект", "Сначала создайте проект или нажмите «Открыть проект».")
        self.open_project()
        return self.project_path is not None

    def open_tool(self, key):
        if key not in ("model", "texture", "logic") and not self.ensure_project():
            return
        bp = str(self.project_path / "BP") if self.project_path else ""
        rp = str(self.project_path / "RP") if self.project_path else ""
        if key == "item":
            ItemEditor(self, bp, rp).exec_()
        elif key == "block":
            BlockEditor(self, bp, rp).exec_()
        elif key == "armor":
            ArmorEditor(self, bp, rp).exec_()
        elif key == "texture":
            TextureEditor(self, str(self.project_path)).exec_()
        elif key == "model":
            ModelWorkspace(self).exec_()
        elif key == "logic":
            LogicWorkspace(self, str(self.project_path)).exec_()
        elif key == "registry":
            TextureRegistryEditor(self, rp).exec_()
        elif key == "examples":
            self.open_examples()

    def open_examples(self):
        if not self.ensure_project():
            return
        folder = self.project_path / "Examples"
        if not folder.exists():
            create_learning_examples(self.project_path)
        QtWidgets.QMessageBox.information(self, "Учебные примеры",
            "Примеры созданы в папке Examples вашего проекта.\\n\\nТам есть предмет, блок, учебная структура биома и события. Откройте JSON-файлы и изучите поле _lesson.")

    def export_project(self):
        if not self.ensure_project():
            return
        suggested = str(self.project_path / (self.project_path.name + ".mcaddon"))
        target, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Куда сохранить аддон", suggested, "Minecraft Add-on (*.mcaddon)")
        if not target:
            return
        try:
            result = export_mcaddon(self.project_path, target)
            report = validate_mcaddon(result)
            QtWidgets.QMessageBox.information(self, "Проверка завершена",
                "Архив создан и прошёл внутреннюю проверку.\\n" + str(result) +
                "\\n\\nВнутри: " + ", ".join(report["packs"]) +
                "\\nJSON-файлов проверено: " + str(report["json_files"]) +
                "\\n\\nТеперь откройте файл на устройстве с Minecraft Bedrock. Программа не может проверить импорт в игру автоматически на этом компьютере.")
            self.statusBar().showMessage("Экспорт завершён.")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Не удалось экспортировать", str(exc))

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())

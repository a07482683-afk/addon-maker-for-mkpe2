# -*- coding: utf-8 -*-
"""Legacy ModPE script and texture workspace for Minecraft PE 1.7.0."""
import json
import re
import shutil
from pathlib import Path

from PySide2 import QtCore, QtWidgets


STARTER = """// ModPE script for Minecraft PE 1.7.0 + compatible BlockLauncher
// Keep IDs in the safe custom range used by your installed script environment.
// Test one feature at a time: old ModPE APIs can differ between BlockLauncher builds.

var MOD_ID = "my_mod";

function newLevel() {
    clientMessage("My ModPE script loaded!");
}

// Example custom item (API availability depends on BlockLauncher build):
// ModPE.setItem(500, "diamond", 0, "My Crystal");
// Player.addItemCreativeInv(500, 1);

// Example custom block (legacy ModPE API; rendering/texture behavior varies):
// Block.defineBlock(200, "Ruby Block", ["ruby_block", 0], 1, false, 0);
// Block.setDestroyTime(200, 2.0);
// Block.setExplosionResistance(200, 6.0);

// Example shaped recipe:
// Level.addShapedRecipe(500, 1, 0,
//     ["DDD", "DRD", "DDD"],
//     ["D", 264, 0, "R", 331, 0]);

// Example entity interaction (not a fully custom mob):
// var mob = Entity.spawnMob(Player.getX() + 2, Player.getY(), Player.getZ(), 10);
// Entity.setNameTag(mob, "Test creature");

function leaveGame() {
    // Cleanup temporary state here.
}
"""

SNIPPETS = {
    "Предмет": """// Новый предмет: ID, текстура, индекс текстуры, имя
ModPE.setItem(500, "diamond", 0, "Мой предмет");
Player.addItemCreativeInv(500, 1);""",
    "Блок": """// Новый блок (ограничения старого ModPE API)
Block.defineBlock(200, "Мой блок", ["my_block", 0], 1, false, 0);
Block.setDestroyTime(200, 2.0);
Block.setExplosionResistance(200, 6.0);""",
    "Крафт": """// Shaped-рецепт: результат ID/количество/метаданные, схема, пары символ-ID-метаданные
Level.addShapedRecipe(500, 1, 0,
    ["DDD", "DRD", "DDD"],
    ["D", 264, 0, "R", 331, 0]);""",
    "Сущность": """// Вызов существующей сущности (это не полноценная новая модель моба)
var mob = Entity.spawnMob(Player.getX() + 2, Player.getY(), Player.getZ(), 10);
Entity.setNameTag(mob, "Моя сущность");""",
    "События": """function useItem(x, y, z, itemId, blockId, side) {
    if (itemId == 500) {
        clientMessage("Использован мой предмет!");
    }
}

function procCmd(command) {
    if (command == "hello") {
        clientMessage("Привет!");
    }
}"""
}


class ModPEStudio(QtWidgets.QDialog):
    def __init__(self, project_path, parent=None):
        super().__init__(parent)
        self.project = Path(project_path)
        self.settings_path = self.project / ".addonmaker.json"
        self.setWindowTitle("MCPE 1.7.0 — ModPE Studio")
        self.resize(1050, 760)
        root = QtWidgets.QVBoxLayout(self)

        header = QtWidgets.QLabel(
            "Профиль MCPE 1.7.0: создавай JavaScript-скрипты ModPE и наборы текстур. "
            "Это старый формат для BlockLauncher, не современный .mcaddon."
        )
        header.setWordWrap(True)
        root.addWidget(header)

        self.tabs = QtWidgets.QTabWidget()
        root.addWidget(self.tabs, 1)
        self._build_script_tab()
        self._build_texture_tab()

        note = QtWidgets.QLabel(
            "Ограничения: набор API зависит от версии BlockLauncher; кастомные блоки/предметы "
            "могут работать не на каждом устройстве. Полноценные новые биомы штатным ModPE "
            "для 1.7.0 не создаются. Сущности — частично, обычно через вызов/изменение "
            "существующих игровых мобов."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#e4c477; padding:8px;")
        root.addWidget(note)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)
        buttons.accepted.connect(self.close)
        root.addWidget(buttons)

    def _build_script_tab(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        row = QtWidgets.QHBoxLayout()
        self.script_name = QtWidgets.QLineEdit("my_mod.js")
        row.addWidget(QtWidgets.QLabel("Файл скрипта:"))
        row.addWidget(self.script_name, 1)
        save = QtWidgets.QPushButton("Сохранить .js")
        save.clicked.connect(self.save_script)
        row.addWidget(save)
        layout.addLayout(row)

        tools = QtWidgets.QHBoxLayout()
        for label in SNIPPETS:
            button = QtWidgets.QPushButton("＋ " + label)
            button.clicked.connect(lambda checked=False, key=label: self.insert_snippet(key))
            tools.addWidget(button)
        tools.addStretch(1)
        layout.addLayout(tools)

        self.code = QtWidgets.QPlainTextEdit()
        self.code.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.code.setTabStopWidth(4)
        self.code.setPlainText(STARTER)
        self.code.setStyleSheet("font-family:Consolas,monospace;font-size:10pt;")
        layout.addWidget(self.code, 1)
        self.tabs.addTab(page, "ModPE-скрипт")

    def _build_texture_tab(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        info = QtWidgets.QLabel(
            "Импортируй PNG как текстуру блока или предмета. Для замены стандартной текстуры "
            "укажи точное имя файла из подходящего texture pack. Файлы сохраняются отдельно "
            "в LegacyTextures, чтобы не портить исходные ресурсы проекта."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        form = QtWidgets.QFormLayout()
        self.texture_kind = QtWidgets.QComboBox()
        self.texture_kind.addItems(["Блоки", "Предметы", "Сущности"])
        self.texture_key = QtWidgets.QLineEdit("my_block")
        self.texture_source = QtWidgets.QLineEdit()
        browse = QtWidgets.QPushButton("Выбрать PNG…")
        browse.clicked.connect(self.choose_png)
        file_row = QtWidgets.QHBoxLayout()
        file_row.addWidget(self.texture_source, 1)
        file_row.addWidget(browse)
        form.addRow("Тип текстуры:", self.texture_kind)
        form.addRow("Имя файла без .png:", self.texture_key)
        form.addRow("PNG:", file_row)
        layout.addLayout(form)
        import_btn = QtWidgets.QPushButton("Добавить текстуру в проект")
        import_btn.clicked.connect(self.import_texture)
        layout.addWidget(import_btn)
        self.texture_status = QtWidgets.QLabel("Текстуры сохраняются в папке LegacyTextures.")
        self.texture_status.setWordWrap(True)
        layout.addWidget(self.texture_status)
        layout.addStretch(1)
        self.tabs.addTab(page, "Текстуры MCPE 1.7.0")

    def insert_snippet(self, key):
        self.code.insertPlainText("\n\n" + SNIPPETS[key] + "\n")

    def save_script(self):
        name = self.script_name.text().strip()
        if not name.lower().endswith(".js"):
            name += ".js"
        if not re.match(r"^[A-Za-z0-9_-]+\.js$", name):
            QtWidgets.QMessageBox.warning(self, "Имя файла", "Используй латинские буквы, цифры, _ и -.")
            return
        folder = self.project / "ModPE"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / name
        if target.exists():
            answer = QtWidgets.QMessageBox.question(
                self, "Заменить файл?", "Такой скрипт уже есть. Заменить его?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return
        target.write_text(self.code.toPlainText(), encoding="utf-8")
        QtWidgets.QMessageBox.information(self, "Сохранено", "ModPE-скрипт сохранён:\n" + str(target))

    def choose_png(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выбрать текстуру PNG", "", "PNG (*.png)")
        if path:
            self.texture_source.setText(path)

    def import_texture(self):
        source = Path(self.texture_source.text().strip())
        key = self.texture_key.text().strip()
        if not source.is_file() or source.suffix.lower() != ".png":
            QtWidgets.QMessageBox.warning(self, "Нужен PNG", "Выбери существующий PNG-файл.")
            return
        if not re.match(r"^[A-Za-z0-9_-]+$", key):
            QtWidgets.QMessageBox.warning(self, "Имя текстуры", "Используй латинские буквы, цифры, _ и -.")
            return
        category = {"Блоки": "blocks", "Предметы": "items", "Сущности": "entities"}[self.texture_kind.currentText()]
        folder = self.project / "LegacyTextures" / category
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / (key + ".png")
        if target.exists():
            answer = QtWidgets.QMessageBox.question(
                self, "Заменить текстуру?", "Файл уже существует. Заменить его?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return
        shutil.copyfile(str(source), str(target))
        self.texture_status.setText("Сохранено: " + str(target) +
            "\nЧтобы заменить стандартную текстуру, используй её точное имя и положи PNG в соответствующую папку texture pack.")
        QtWidgets.QMessageBox.information(self, "Текстура добавлена", str(target))

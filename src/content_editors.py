import json
import re
from pathlib import Path
from PySide2 import QtCore, QtWidgets


IDENTIFIER_RE = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")


class DefinitionEditor(QtWidgets.QDialog):
    """Small JSON-first editor for one Bedrock content definition."""

    folder_name = ""
    title_text = "Definition"
    default_namespace = "demo"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.title_text)
        self.resize(820, 680)
        root = QtWidgets.QVBoxLayout(self)

        form_box = QtWidgets.QGroupBox("Definition")
        form = QtWidgets.QFormLayout(form_box)
        self.identifier = QtWidgets.QLineEdit("demo:my_" + self.folder_name[:-1])
        self.display_name = QtWidgets.QLineEdit("My " + self.folder_name[:-1].title())
        form.addRow("Identifier (namespace:name)", self.identifier)
        form.addRow("Display name", self.display_name)
        self.add_fields(form)
        root.addWidget(form_box)

        project_row = QtWidgets.QHBoxLayout()
        self.bp_path = QtWidgets.QLineEdit()
        self.bp_path.setPlaceholderText("Choose the Behavior Pack (BP) folder")
        browse = QtWidgets.QPushButton("Choose BP…")
        browse.clicked.connect(self.choose_bp)
        project_row.addWidget(self.bp_path, 1)
        project_row.addWidget(browse)
        root.addLayout(project_row)

        root.addWidget(QtWidgets.QLabel("Bedrock JSON preview"))
        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        root.addWidget(self.preview, 1)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        save = QtWidgets.QPushButton("Save into BP")
        save.clicked.connect(self.save_definition)
        buttons.addWidget(save)
        root.addLayout(buttons)

        self.identifier.textChanged.connect(self.refresh_preview)
        self.display_name.textChanged.connect(self.refresh_preview)
        self.connect_fields()
        self.refresh_preview()

    def add_fields(self, form):
        pass

    def connect_fields(self):
        pass

    def definition(self):
        raise NotImplementedError

    def refresh_preview(self, *_):
        try:
            self.preview.setPlainText(json.dumps(self.definition(), indent=2, ensure_ascii=False))
        except Exception as exc:
            self.preview.setPlainText("Cannot generate preview: " + str(exc))

    def choose_bp(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose Behavior Pack folder")
        if folder:
            self.bp_path.setText(folder)

    def save_definition(self):
        identifier = self.identifier.text().strip()
        if not IDENTIFIER_RE.match(identifier):
            QtWidgets.QMessageBox.warning(
                self, "Invalid identifier",
                "Use lowercase namespace:name, for example demo:crystal_block.")
            return
        bp = Path(self.bp_path.text().strip())
        if not bp.is_dir():
            QtWidgets.QMessageBox.warning(self, "Choose BP", "Choose an existing Behavior Pack folder first.")
            return
        namespace, name = identifier.split(":", 1)
        safe_name = name.replace("/", "_")
        target = bp / self.folder_name / (safe_name + ".json")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(self.definition(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            QtWidgets.QMessageBox.information(self, "Saved", "Definition saved to:\n" + str(target))
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(exc))


class ItemEditor(DefinitionEditor):
    folder_name = "items"
    title_text = "Items & Materials Editor"

    def add_fields(self, form):
        self.stack = QtWidgets.QSpinBox()
        self.stack.setRange(1, 64)
        self.stack.setValue(64)
        self.category = QtWidgets.QComboBox()
        self.category.addItems(["items", "equipment", "nature"])
        self.icon = QtWidgets.QLineEdit("my_item")
        self.foil = QtWidgets.QCheckBox("Glint effect")
        form.addRow("Creative category", self.category)
        form.addRow("Texture key", self.icon)
        form.addRow("Maximum stack", self.stack)
        form.addRow("Visual effect", self.foil)

    def connect_fields(self):
        for widget, signal in (
            (self.stack, self.stack.valueChanged),
            (self.category, self.category.currentTextChanged),
            (self.icon, self.icon.textChanged),
            (self.foil, self.foil.toggled),
        ):
            signal.connect(self.refresh_preview)

    def definition(self):
        identifier = self.identifier.text().strip()
        texture = self.icon.text().strip() or identifier.split(":")[-1]
        return {
            "format_version": "1.20.0",
            "minecraft:item": {
                "description": {
                    "identifier": identifier,
                    "menu_category": {"category": self.category.currentText()}
                },
                "components": {
                    "minecraft:display_name": {"value": self.display_name.text()},
                    "minecraft:icon": {"texture": texture},
                    "minecraft:max_stack_size": self.stack.value(),
                    "minecraft:foil": self.foil.isChecked()
                }
            }
        }


class BlockEditor(DefinitionEditor):
    folder_name = "blocks"
    title_text = "Blocks Editor"

    def add_fields(self, form):
        self.category = QtWidgets.QComboBox()
        self.category.addItems(["construction", "nature", "items"])
        self.hardness = QtWidgets.QDoubleSpinBox()
        self.hardness.setRange(0.0, 100.0)
        self.hardness.setSingleStep(0.5)
        self.hardness.setValue(1.5)
        self.friction = QtWidgets.QDoubleSpinBox()
        self.friction.setRange(0.0, 1.0)
        self.friction.setSingleStep(0.05)
        self.friction.setValue(0.6)
        self.light = QtWidgets.QSpinBox()
        self.light.setRange(0, 15)
        self.map_color = QtWidgets.QLineEdit("#7F7F7F")
        form.addRow("Creative category", self.category)
        form.addRow("Mining time (seconds)", self.hardness)
        form.addRow("Friction", self.friction)
        form.addRow("Light emission (0–15)", self.light)
        form.addRow("Map color", self.map_color)

    def connect_fields(self):
        for signal in (
            self.category.currentTextChanged,
            self.hardness.valueChanged,
            self.friction.valueChanged,
            self.light.valueChanged,
            self.map_color.textChanged,
        ):
            signal.connect(self.refresh_preview)

    def definition(self):
        color = self.map_color.text().strip()
        if not re.match(r"^#[0-9a-fA-F]{6}$", color):
            color = "#7F7F7F"
        return {
            "format_version": "1.20.0",
            "minecraft:block": {
                "description": {
                    "identifier": self.identifier.text().strip(),
                    "menu_category": {"category": self.category.currentText()}
                },
                "components": {
                    "minecraft:display_name": self.display_name.text(),
                    "minecraft:destructible_by_mining": {"seconds_to_destroy": self.hardness.value()},
                    "minecraft:friction": self.friction.value(),
                    "minecraft:light_emission": self.light.value(),
                    "minecraft:map_color": color
                }
            }
        }

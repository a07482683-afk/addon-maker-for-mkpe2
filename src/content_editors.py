import json
import re
from pathlib import Path
from PySide2 import QtCore, QtGui, QtWidgets


IDENTIFIER_RE = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")


class DefinitionEditor(QtWidgets.QDialog):
    """Small JSON-first editor for one Bedrock content definition."""

    folder_name = ""
    title_text = "Настройки"
    default_namespace = "demo"

    def __init__(self, parent=None, bp_path=None, rp_path=None):
        super().__init__(parent)
        self.rp_path = Path(rp_path) if rp_path else None
        self.setWindowTitle(self.title_text)
        self.resize(820, 680)
        root = QtWidgets.QVBoxLayout(self)

        form_box = QtWidgets.QGroupBox("Настройки предмета или блока")
        form = QtWidgets.QFormLayout(form_box)
        self.identifier = QtWidgets.QLineEdit("demo:my_" + self.folder_name[:-1])
        self.display_name = QtWidgets.QLineEdit("My " + self.folder_name[:-1].title())
        form.addRow("ID (например demo:my_item)", self.identifier)
        form.addRow("Название в игре", self.display_name)
        self.add_fields(form)
        root.addWidget(form_box)

        project_row = QtWidgets.QHBoxLayout()
        self.bp_path = QtWidgets.QLineEdit(bp_path or "")
        self.bp_path.setPlaceholderText("Папка BP выбрана автоматически")
        browse = QtWidgets.QPushButton("Выбрать BP…")
        browse.clicked.connect(self.choose_bp)
        project_row.addWidget(self.bp_path, 1)
        project_row.addWidget(browse)
        root.addLayout(project_row)

        root.addWidget(QtWidgets.QLabel("Предпросмотр файла (можно не менять)"))
        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        root.addWidget(self.preview, 1)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        save = QtWidgets.QPushButton("Сохранить в проект")
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
                self, "Неверный ID",
                "Use lowercase namespace:name, for example demo:crystal_block.")
            return
        bp = Path(self.bp_path.text().strip())
        if not bp.is_dir():
            QtWidgets.QMessageBox.warning(self, "Выберите папку BP", "Сначала выберите существующую папку Behavior Pack (BP).")
            return
        namespace, name = identifier.split(":", 1)
        safe_name = name.replace("/", "_")
        target = bp / self.folder_name / (safe_name + ".json")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(self.definition(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            QtWidgets.QMessageBox.information(self, "Сохранено", "Definition saved to:\n" + str(target))
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка сохранения", str(exc))



class PixelIconCanvas(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 320)
        self.image = QtGui.QImage(16, 16, QtGui.QImage.Format_ARGB32)
        self.image.fill(QtCore.Qt.transparent)
        self.color = QtGui.QColor("#65d7ff")
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("#20242d"))
        for y in range(16):
            for x in range(16):
                if (x + y) % 2 == 0:
                    painter.fillRect(x*20, y*20, 20, 20, QtGui.QColor("#343a46"))
        painter.drawImage(self.rect(), self.image)
        painter.setPen(QtGui.QPen(QtGui.QColor(255,255,255,45), 1))
        for i in range(17):
            painter.drawLine(i*20, 0, i*20, 320)
            painter.drawLine(0, i*20, 320, i*20)
    def paint_at(self, pos, erase=False):
        x, y = pos.x() // 20, pos.y() // 20
        if 0 <= x < 16 and 0 <= y < 16:
            p = QtGui.QPainter(self.image)
            p.fillRect(x, y, 1, 1, QtGui.QColor(0, 0, 0, 0) if erase else self.color)
            p.end()
            self.update()
    def mousePressEvent(self, event):
        self.paint_at(event.pos(), event.button() == QtCore.Qt.RightButton)
    def mouseMoveEvent(self, event):
        if event.buttons() & (QtCore.Qt.LeftButton | QtCore.Qt.RightButton):
            self.paint_at(event.pos(), bool(event.buttons() & QtCore.Qt.RightButton))


class PixelIconDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Нарисовать иконку предмета — 16×16")
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("ЛКМ — рисовать. ПКМ — стирать. Иконка сохранится в Resource Pack."))
        self.canvas = PixelIconCanvas()
        layout.addWidget(self.canvas, 0, QtCore.Qt.AlignCenter)
        row = QtWidgets.QHBoxLayout()
        color = QtWidgets.QPushButton("Выбрать цвет")
        color.clicked.connect(self.choose_color)
        clear = QtWidgets.QPushButton("Очистить")
        clear.clicked.connect(self.clear)
        row.addWidget(color)
        row.addWidget(clear)
        row.addStretch(1)
        layout.addLayout(row)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Save).setText("Использовать иконку")
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor(self.canvas.color, self, "Цвет пикселя", QtWidgets.QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.canvas.color = color
    def clear(self):
        self.canvas.image.fill(QtCore.Qt.transparent)
        self.canvas.update()

class ItemEditor(DefinitionEditor):
    folder_name = "items"
    title_text = "Редактор предметов и материалов"

    def add_fields(self, form):
        self.stack = QtWidgets.QSpinBox()
        self.stack.setRange(1, 64)
        self.stack.setValue(64)
        self.category = QtWidgets.QComboBox()
        self.category.addItems(["items", "equipment", "nature"])
        self.icon = QtWidgets.QLineEdit("my_item")
        self.foil = QtWidgets.QCheckBox("Свечение предмета")
        form.addRow("Категория в творческом режиме", self.category)
        form.addRow("Имя текстуры", self.icon)
        form.addRow("Размер стопки", self.stack)

        form.addRow("Эффект свечения", self.foil)
        self.draw_icon = QtWidgets.QPushButton("Нарисовать иконку 16×16…")
        self.draw_icon.clicked.connect(self.open_icon_painter)
        form.addRow("Иконка предмета", self.draw_icon)
        self.icon_status = QtWidgets.QLabel("Иконка пока не нарисована")
        form.addRow("", self.icon_status)

    def open_icon_painter(self):
        dialog = PixelIconDialog(self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not self.rp_path or not self.rp_path.is_dir():
            QtWidgets.QMessageBox.warning(self, "Нет Resource Pack", "Сначала создай или открой проект с папкой RP.")
            return
        key = self.icon.text().strip() or self.identifier.text().split(":")[-1]
        key = re.sub(r"[^a-zA-Z0-9_./-]", "_", key)
        target = self.rp_path / "textures" / "items" / (key.replace("/", "_") + ".png")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not dialog.canvas.image.save(str(target), "PNG"):
            QtWidgets.QMessageBox.critical(self, "Ошибка", "Не удалось сохранить PNG.")
            return
        atlas_path = self.rp_path / "textures" / "item_texture.json"
        atlas = {"resource_pack_name": "addon", "texture_name": "atlas.items", "texture_data": {}}
        if atlas_path.is_file():
            try:
                atlas = json.loads(atlas_path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Ошибка атласа", "Не удалось прочитать item_texture.json: " + str(exc))
                return
        atlas.setdefault("texture_data", {})[key] = {"textures": "textures/items/" + target.stem}
        atlas_path.parent.mkdir(parents=True, exist_ok=True)
        atlas_path.write_text(json.dumps(atlas, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
        self.icon.setText(key)
        self.icon_status.setText("Иконка сохранена: " + str(target))


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
    title_text = "Редактор блоков"

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
        form.addRow("Категория в творческом режиме", self.category)
        form.addRow("Время разрушения (секунды)", self.hardness)
        form.addRow("Скольжение", self.friction)
        form.addRow("Излучение света (0–15)", self.light)
        form.addRow("Цвет на карте", self.map_color)

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


class ArmorEditor(DefinitionEditor):
    """Starter Bedrock wearable item editor."""
    folder_name = "items"
    title_text = "Armor & Wearables Editor"

    def add_fields(self, form):
        self.slot = QtWidgets.QComboBox()
        self.slot.addItems(["slot.armor.head", "slot.armor.chest", "slot.armor.legs", "slot.armor.feet"])
        self.protection = QtWidgets.QSpinBox()
        self.protection.setRange(0, 30)
        self.protection.setValue(2)
        self.durability = QtWidgets.QSpinBox()
        self.durability.setRange(1, 10000)
        self.durability.setValue(250)
        self.icon = QtWidgets.QLineEdit("my_armor")
        self.stack = QtWidgets.QSpinBox()
        self.stack.setRange(1, 64)
        self.stack.setValue(1)
        form.addRow("Слот брони", self.slot)
        form.addRow("Защита", self.protection)
        form.addRow("Maximum durability", self.durability)
        form.addRow("Имя текстуры", self.icon)
        form.addRow("Размер стопки", self.stack)

    def connect_fields(self):
        for signal in (self.slot.currentTextChanged, self.protection.valueChanged,
                       self.durability.valueChanged, self.icon.textChanged,
                       self.stack.valueChanged):
            signal.connect(self.refresh_preview)

    def definition(self):
        identifier = self.identifier.text().strip()
        texture = self.icon.text().strip() or identifier.split(":")[-1]
        return {
            "format_version": "1.20.0",
            "minecraft:item": {
                "description": {
                    "identifier": identifier,
                    "menu_category": {"category": "equipment"}
                },
                "components": {
                    "minecraft:display_name": {"value": self.display_name.text()},
                    "minecraft:icon": {"texture": texture},
                    "minecraft:max_stack_size": self.stack.value(),
                    "minecraft:wearable": {
                        "slot": self.slot.currentText(),
                        "protection": self.protection.value()
                    },
                    "minecraft:durability": {"max_durability": self.durability.value()}
                }
            }
        }


class TextureRegistryEditor(QtWidgets.QDialog):
    """Copies PNG item icons into RP and maintains textures/item_texture.json."""
    def __init__(self, parent=None, rp_path=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить текстуру в проект")
        self.resize(760, 520)
        root = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.rp_path = QtWidgets.QLineEdit(rp_path or "")
        browse = QtWidgets.QPushButton("Выбрать RP…")
        browse.clicked.connect(self.choose_rp)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.rp_path, 1)
        row.addWidget(browse)
        form.addRow("Папка ресурсов RP", row)
        self.key = QtWidgets.QLineEdit("my_item")
        form.addRow("Имя текстуры", self.key)
        self.image_path = QtWidgets.QLineEdit()
        pick = QtWidgets.QPushButton("Choose PNG…")
        pick.clicked.connect(self.choose_png)
        image_row = QtWidgets.QHBoxLayout()
        image_row.addWidget(self.image_path, 1)
        image_row.addWidget(pick)
        form.addRow("Картинка PNG", image_row)
        root.addLayout(form)
        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setReadOnly(True)
        root.addWidget(QtWidgets.QLabel("Предпросмотр записи текстуры"))
        root.addWidget(self.preview, 1)
        self.key.textChanged.connect(self.refresh_preview)
        save = QtWidgets.QPushButton("Добавить текстуру в проект")
        save.clicked.connect(self.register_texture)
        root.addWidget(save)
        self.refresh_preview()

    def choose_rp(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose Resource Pack folder")
        if folder:
            self.rp_path.setText(folder)

    def choose_png(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose PNG texture", "", "PNG images (*.png)")
        if filename:
            self.image_path.setText(filename)

    def atlas_path(self):
        return Path(self.rp_path.text().strip()) / "textures" / "item_texture.json"

    def atlas_data(self):
        path = self.atlas_path()
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                if not isinstance(data, dict):
                    raise ValueError("Atlas root must be a JSON object.")
            except Exception as exc:
                raise ValueError("Cannot read item_texture.json: " + str(exc))
        else:
            data = {"resource_pack_name": "Addon Maker", "texture_name": "atlas.items", "texture_data": {}}
        data.setdefault("resource_pack_name", "Addon Maker")
        data.setdefault("texture_name", "atlas.items")
        data.setdefault("texture_data", {})
        if not isinstance(data["texture_data"], dict):
            raise ValueError("texture_data must be a JSON object.")
        return data

    def refresh_preview(self, *_):
        key = self.key.text().strip()
        entry = {key: {"textures": "textures/items/" + key}} if key else {}
        self.preview.setPlainText(json.dumps(entry, indent=2, ensure_ascii=False))

    def register_texture(self):
        key = self.key.text().strip()
        rp = Path(self.rp_path.text().strip())
        source = Path(self.image_path.text().strip())
        if not re.match(r"^[a-z0-9_]+$", key):
            QtWidgets.QMessageBox.warning(self, "Invalid key", "Use lowercase letters, digits and underscores.")
            return
        if not rp.is_dir():
            QtWidgets.QMessageBox.warning(self, "Выберите папку RP", "Выберите существующую папку Resource Pack (RP).")
            return
        if not source.is_file() or source.suffix.lower() != ".png":
            QtWidgets.QMessageBox.warning(self, "Choose PNG", "Select a valid PNG image.")
            return
        try:
            import shutil
            texture_dir = rp / "textures" / "items"
            texture_dir.mkdir(parents=True, exist_ok=True)
            target = texture_dir / (key + ".png")
            if target.exists():
                answer = QtWidgets.QMessageBox.question(
                    self, "Replace texture?", "A texture with this key already exists. Replace it?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if answer != QtWidgets.QMessageBox.Yes:
                    return
            shutil.copyfile(str(source), str(target))
            atlas = self.atlas_data()
            atlas["texture_data"][key] = {"textures": "textures/items/" + key}
            path = self.atlas_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(atlas, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            QtWidgets.QMessageBox.information(
                self, "Registered", "Texture copied to:\n" + str(target) +
                "\n\nAtlas updated:\n" + str(path))
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Registration failed", str(exc))

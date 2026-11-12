import json
import zipfile
from pathlib import Path
from PySide2 import QtCore, QtGui, QtWidgets


class TextureCanvas(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 420)
        base = QtGui.QImage(64, 64, QtGui.QImage.Format_ARGB32)
        base.fill(QtCore.Qt.transparent)
        self.layers = [{"name": "Layer 1", "image": base, "visible": True, "opacity": 1.0}]
        self.active_layer = 0
        self.color = QtGui.QColor("#6f83ff")
        self.tool = "Карандаш"
        self.grid = True
        self.last = None
        self.undo_stack = []
        self.setMouseTracking(True)

    @property
    def image(self):
        return self.layers[self.active_layer]["image"]

    @image.setter
    def image(self, value):
        self.layers[self.active_layer]["image"] = value

    def composite(self):
        w, h = self.image.width(), self.image.height()
        result = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32)
        result.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(result)
        for layer in self.layers:
            if layer["visible"]:
                painter.setOpacity(layer["opacity"])
                painter.drawImage(0, 0, layer["image"])
        painter.end()
        return result

    def snapshot(self):
        self.undo_stack.append((self.active_layer, self.image.copy()))
        if len(self.undo_stack) > 40:
            self.undo_stack.pop(0)

    def undo(self):
        if self.undo_stack:
            index, image = self.undo_stack.pop()
            if index < len(self.layers):
                self.active_layer = index
                self.layers[index]["image"] = image
            self.update()

    def add_layer(self, name=None):
        image = QtGui.QImage(self.image.size(), QtGui.QImage.Format_ARGB32)
        image.fill(QtCore.Qt.transparent)
        self.layers.append({"name": name or "Layer %d" % (len(self.layers)+1),
                            "image": image, "visible": True, "opacity": 1.0})
        self.active_layer = len(self.layers)-1
        self.update()

    def remove_layer(self):
        if len(self.layers) <= 1:
            return False
        self.layers.pop(self.active_layer)
        self.active_layer = max(0, self.active_layer-1)
        self.update()
        return True

    def move_layer(self, direction):
        target = self.active_layer + direction
        if 0 <= target < len(self.layers):
            self.layers[self.active_layer], self.layers[target] = self.layers[target], self.layers[self.active_layer]
            self.active_layer = target
            self.update()

    def set_size(self, w, h):
        self.snapshot()
        for layer in self.layers:
            layer["image"] = layer["image"].scaled(w, h, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.FastTransformation)
        self.update()

    def point_for(self, pos):
        x = int(pos.x() * self.image.width() / max(1, self.width()))
        y = int(pos.y() * self.image.height() / max(1, self.height()))
        return QtCore.QPoint(max(0, min(self.image.width()-1, x)),
                             max(0, min(self.image.height()-1, y)))

    def mousePressEvent(self, event):
        p = self.point_for(event.pos())
        if self.tool == "Eyedropper":
            self.color = self.composite().pixelColor(p)
            return
        self.snapshot()
        self.last = p
        self.apply(p)

    def mouseMoveEvent(self, event):
        if self.last is not None and event.buttons() & QtCore.Qt.LeftButton:
            p = self.point_for(event.pos())
            if self.tool in ("Pencil", "Eraser"):
                self.draw_line(self.last, p)
            self.last = p

    def mouseReleaseEvent(self, event):
        self.last = None

    def apply(self, p):
        if self.tool == "Fill":
            self.flood_fill(p)
        else:
            painter = QtGui.QPainter(self.image)
            if self.tool == "Eraser":
                painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            else:
                painter.setPen(QtGui.QPen(self.color))
            painter.drawPoint(p)
            painter.end()
        self.update()

    def draw_line(self, a, b):
        painter = QtGui.QPainter(self.image)
        if self.tool == "Eraser":
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
        else:
            painter.setPen(QtGui.QPen(self.color, 1))
        painter.drawLine(a, b)
        painter.end()
        self.update()

    def flood_fill(self, start):
        target = self.image.pixelColor(start)
        replacement = self.color
        if target == replacement:
            return
        w, h = self.image.width(), self.image.height()
        stack = [(start.x(), start.y())]
        seen = set()
        while stack:
            x, y = stack.pop()
            if (x, y) in seen or x < 0 or y < 0 or x >= w or y >= h:
                continue
            seen.add((x, y))
            if self.image.pixelColor(x, y) != target:
                continue
            self.image.setPixelColor(x, y, replacement)
            stack.extend(((x+1,y),(x-1,y),(x,y+1),(x,y-1)))
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("#11141b"))
        w, h = self.image.width(), self.image.height()
        cell_w, cell_h = self.width()/w, self.height()/h
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, False)
        for y in range(h):
            for x in range(w):
                if (x+y) % 2 == 0:
                    painter.fillRect(QtCore.QRectF(x*cell_w,y*cell_h,cell_w,cell_h), QtGui.QColor("#252a35"))
                else:
                    painter.fillRect(QtCore.QRectF(x*cell_w,y*cell_h,cell_w,cell_h), QtGui.QColor("#1c2029"))
        painter.drawImage(self.rect(), self.composite())
        if self.grid and cell_w >= 5 and cell_h >= 5:
            painter.setPen(QtGui.QPen(QtGui.QColor(255,255,255,35), 0))
            for x in range(w+1):
                painter.drawLine(QtCore.QPointF(x*cell_w,0), QtCore.QPointF(x*cell_w,self.height()))
            for y in range(h+1):
                painter.drawLine(QtCore.QPointF(0,y*cell_h), QtCore.QPointF(self.width(),y*cell_h))


class TextureEditor(QtWidgets.QDialog):
    def __init__(self, parent=None, project_path=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор текстур — рисование иконок и текстур")
        self.project_path = Path(project_path) if project_path else None
        self.resize(1180, 760)
        root = QtWidgets.QVBoxLayout(self)
        top = QtWidgets.QHBoxLayout()
        self.size_box = QtWidgets.QComboBox()
        for size in ("16 × 16", "32 × 32", "64 × 64", "128 × 128", "256 × 256"):
            self.size_box.addItem(size)
        self.size_box.setCurrentIndex(2)
        self.size_box.currentIndexChanged.connect(self.change_size)
        top.addWidget(QtWidgets.QLabel("Размер холста"))
        top.addWidget(self.size_box)
        self.grid_box = QtWidgets.QCheckBox("Сетка пикселей")
        self.grid_box.setChecked(True)
        self.grid_box.toggled.connect(self.toggle_grid)
        top.addWidget(self.grid_box)
        top.addStretch(1)
        for label, callback in (("Отменить", self.undo), ("Открыть PNG", self.open_image),
                                ("Открыть проект", self.open_project), ("Сохранить проект", self.save_project),
                                ("Экспорт PNG", self.save_image)):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(callback)
            top.addWidget(button)
        root.addLayout(top)

        body = QtWidgets.QHBoxLayout()
        tools = QtWidgets.QVBoxLayout()
        self.canvas = TextureCanvas()
        for tool in ("Карандаш", "Ластик", "Заливка", "Пипетка"):
            b = QtWidgets.QPushButton(tool)
            b.clicked.connect(lambda checked=False, t=tool: self.set_tool(t))
            tools.addWidget(b)
        color_btn = QtWidgets.QPushButton("Выбрать цвет")
        color_btn.clicked.connect(self.choose_color)
        tools.addWidget(color_btn)
        self.color_preview = QtWidgets.QLabel("  ")
        self.color_preview.setFixedHeight(32)
        self.color_preview.setStyleSheet("background:#6f83ff;border:1px solid #555;border-radius:5px;")
        tools.addWidget(self.color_preview)
        tools.addStretch(1)
        body.addLayout(tools)
        body.addWidget(self.canvas, 1)

        layer_panel = QtWidgets.QVBoxLayout()
        layer_panel.addWidget(QtWidgets.QLabel("СЛОИ"))
        self.layer_list = QtWidgets.QListWidget()
        self.layer_list.currentRowChanged.connect(self.select_layer)
        layer_panel.addWidget(self.layer_list, 1)
        for label, callback in (("＋ Добавить", self.add_layer), ("Дублировать", self.duplicate_layer),
                                ("Переименовать", self.rename_layer), ("− Удалить", self.delete_layer),
                                ("Вверх", lambda: self.move_layer(1)),
                                ("Вниз", lambda: self.move_layer(-1))):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(callback)
            layer_panel.addWidget(button)
        self.layer_list.itemChanged.connect(self.layer_visibility_changed)
        layer_panel.addWidget(QtWidgets.QLabel("Непрозрачность слоя"))
        self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        layer_panel.addWidget(self.opacity_slider)
        body.addLayout(layer_panel)
        root.addLayout(body, 1)
        self.status = QtWidgets.QLabel("Карандаш • 64 × 64 • Прозрачный фон")
        root.addWidget(self.status)
        self.refresh_layers()

    def refresh_layers(self):
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for layer in reversed(self.canvas.layers):
            item = QtWidgets.QListWidgetItem(layer["name"])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable)
            item.setCheckState(QtCore.Qt.Checked if layer["visible"] else QtCore.Qt.Unchecked)
            self.layer_list.addItem(item)
        self.layer_list.setCurrentRow(len(self.canvas.layers)-1-self.canvas.active_layer)
        self.layer_list.blockSignals(False)
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(int(self.canvas.layers[self.canvas.active_layer]["opacity"] * 100))
        self.opacity_slider.blockSignals(False)

    def select_layer(self, row):
        if row >= 0:
            self.canvas.active_layer = len(self.canvas.layers)-1-row
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(int(self.canvas.layers[self.canvas.active_layer]["opacity"] * 100))
            self.opacity_slider.blockSignals(False)
            self.canvas.update()

    def change_opacity(self, value):
        self.canvas.layers[self.canvas.active_layer]["opacity"] = value / 100.0
        self.canvas.update()

    def duplicate_layer(self):
        source = self.canvas.layers[self.canvas.active_layer]
        self.canvas.add_layer(source["name"] + " copy")
        self.canvas.image = source["image"].copy()
        self.canvas.layers[self.canvas.active_layer]["opacity"] = source["opacity"]
        self.refresh_layers()

    def rename_layer(self):
        layer = self.canvas.layers[self.canvas.active_layer]
        name, ok = QtWidgets.QInputDialog.getText(self, "Переименовать слой", "Название слоя:", text=layer["name"])
        if ok and name.strip():
            layer["name"] = name.strip()
            self.refresh_layers()

    def layer_visibility_changed(self, item):
        index = self.layer_list.row(item)
        layer_index = len(self.canvas.layers)-1-index
        if 0 <= layer_index < len(self.canvas.layers):
            self.canvas.layers[layer_index]["visible"] = item.checkState() == QtCore.Qt.Checked
            self.canvas.update()

    def add_layer(self):
        self.canvas.add_layer()
        self.refresh_layers()

    def delete_layer(self):
        if self.canvas.remove_layer():
            self.refresh_layers()
        else:
            QtWidgets.QMessageBox.information(self, "Слои", "У текстуры должен остаться хотя бы один слой.")

    def move_layer(self, direction):
        self.canvas.move_layer(direction)
        self.refresh_layers()

    def undo(self):
        self.canvas.undo()
        self.refresh_layers()

    def set_tool(self, tool):
        internal = {"Карандаш": "Pencil", "Ластик": "Eraser", "Заливка": "Fill", "Пипетка": "Eyedropper"}
        self.canvas.tool = internal.get(tool, "Pencil")
        self.status.setText(tool + " • %d × %d" % (self.canvas.image.width(), self.canvas.image.height()))

    def change_size(self, index):
        size = (16,32,64,128,256)[index]
        self.canvas.set_size(size, size)
        self.status.setText("Размер холста: %d × %d" % (size,size))

    def toggle_grid(self, enabled):
        self.canvas.grid = enabled
        self.canvas.update()

    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor(self.canvas.color, self, "Цвет текстуры", QtWidgets.QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.canvas.color = color
            self.color_preview.setStyleSheet("background:%s;border:1px solid #555;border-radius:5px;" % color.name())
            self.status.setText("Цвет: " + color.name())

    def open_image(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Открыть текстуру", "", "Images (*.png *.jpg *.bmp)")
        if path:
            image = QtGui.QImage(path)
            if not image.isNull():
                self.canvas.snapshot()
                self.canvas.add_layer(Path(path).stem)
                self.canvas.image = image.convertToFormat(QtGui.QImage.Format_ARGB32)
                self.canvas.update()
                self.refresh_layers()
                self.status.setText("Добавлен новый слой: " + Path(path).name)

    def save_image(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Экспорт текстуры", "texture.png", "PNG image (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            if self.canvas.composite().save(path, "PNG"):
                self.status.setText("Текстура PNG сохранена: " + path)
            else:
                QtWidgets.QMessageBox.warning(self, "Export failed", "Не удалось сохранить PNG-файл.")

    def save_project(self):
        default = str(self.project_path / "TextureProjects" / "texture.tstudio") if self.project_path else "texture.tstudio"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить проект текстуры", default, "Проект текстуры (*.tstudio)")
        if not path:
            return
        if not path.lower().endswith(".tstudio"):
            path += ".tstudio"
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                metadata = {"format_version": 1, "active_layer": self.canvas.active_layer, "layers": []}
                for index, layer in enumerate(self.canvas.layers):
                    buffer = QtCore.QBuffer()
                    buffer.open(QtCore.QIODevice.WriteOnly)
                    layer["image"].save(buffer, "PNG")
                    archive.writestr("layers/layer_%03d.png" % index, bytes(buffer.data()))
                    metadata["layers"].append({"name": layer["name"], "visible": layer["visible"],
                                                "opacity": layer["opacity"],
                                                "file": "layers/layer_%03d.png" % index})
                archive.writestr("project.json", json.dumps(metadata, indent=2, ensure_ascii=False))
            self.status.setText("Проект текстуры сохранён: " + path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка сохранения", str(exc))

    def open_project(self):
        start = str(self.project_path / "TextureProjects") if self.project_path and (self.project_path / "TextureProjects").is_dir() else ""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Открыть проект текстуры", start, "Проект текстуры (*.tstudio)")
        if not path:
            return
        try:
            with zipfile.ZipFile(path, "r") as archive:
                metadata = json.loads(archive.read("project.json").decode("utf-8"))
                layers = []
                for item in metadata["layers"]:
                    image = QtGui.QImage()
                    if not image.loadFromData(archive.read(item["file"]), "PNG"):
                        raise ValueError("Could not read " + item["file"])
                    layers.append({"name": item["name"], "image": image,
                                   "visible": bool(item.get("visible", True)),
                                   "opacity": float(item.get("opacity", 1.0))})
                if not layers:
                    raise ValueError("Project contains no layers.")
                self.canvas.layers = layers
                self.canvas.active_layer = max(0, min(len(layers)-1, int(metadata.get("active_layer", 0))))
                self.canvas.undo_stack = []
                self.canvas.update()
                self.refresh_layers()
                self.status.setText("Открыт проект текстуры: " + Path(path).name)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка открытия", str(exc))


class EventSheetEditor(QtWidgets.QWidget):
    TRIGGERS = {
        "Игрок появляется в мире": "playerSpawn",
        "Игрок уходит из мира": "playerLeave",
        "Игрок использует предмет": "itemUse",
        "Игрок использует предмет на блоке": "itemUseOn",
        "Игрок ломает блок": "playerBreakBlock",
        "Игрок ставит блок": "playerPlaceBlock",
        "Игрок взаимодействует с блоком": "playerInteractWithBlock",
        "Игрок взаимодействует с сущностью": "playerInteractWithEntity",
        "Игрок атакует сущность": "entityHurt",
        "Сущность получает урон": "entityHurt",
        "Сущность умирает": "entityDie",
        "Сущность появляется": "entitySpawn",
        "Снаряд попадает в блок": "projectileHitBlock",
        "Снаряд попадает в сущность": "projectileHitEntity",
        "Предмет выброшен": "itemStopUse",
        "Игрок начинает использовать предмет": "itemStartUse",
        "Игрок заканчивает использовать предмет": "itemStopUse",
        "Игрок прыгает": "entityJump",
        "Игрок садится на ездового моба": "entityMount",
        "Игрок слезает с ездового моба": "entityDismount",
        "Погода меняется": "weatherChange",
        "Время суток меняется": "timeOfDay",
        "Сущность входит в измерение": "entityDimensionChange",
        "Игрок подбирает предмет": "playerInventoryItemChange",
        "Игрок меняет слот": "playerHotbarSelectedSlotChange",
        "Игрок начинает приседать": "playerButtonInput",
        "Игрок спит": "playerInteractWithBlock",
        "Игрок возрождается": "playerSpawn"
    }
    ACTIONS = [
        "Отправить сообщение в чат", "Выполнить команду", "Выдать предмет",
        "Добавить эффект", "Воспроизвести звук", "Создать частицу",
        "Телепортировать игрока", "Добавить тег", "Убрать тег",
        "Изменить погоду", "Изменить время", "Показать название",
        "Удалить предмет из руки", "Добавить опыт", "Выполнить JavaScript"
    ]
    COLORS = ["#26364a", "#3a2e4c", "#25433e", "#4a352d", "#3b3d27", "#293d4a"]

    def __init__(self, parent=None, project_path=None):
        super().__init__(parent)
        self.project_path = Path(project_path) if project_path else None
        self.setWindowTitle("Конструктор событий — WHEN → DO")
        root = QtWidgets.QVBoxLayout(self)
        bar = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Конструктор событий")
        title.setStyleSheet("font-size:18pt;font-weight:700;")
        bar.addWidget(title)
        bar.addStretch(1)
        add = QtWidgets.QPushButton("＋ Добавить событие")
        add.clicked.connect(self.add_event)
        save = QtWidgets.QPushButton("Сохранить")
        save.clicked.connect(self.save_sheet)
        generate = QtWidgets.QPushButton("Создать JavaScript")
        generate.clicked.connect(self.generate_javascript)
        bar.addWidget(add); bar.addWidget(save); bar.addWidget(generate)
        root.addLayout(bar)
        hint = QtWidgets.QLabel("WHEN — что произошло. DO — что должна сделать игра. Можно добавить сколько угодно правил и менять цвет каждой карточки.")
        hint.setWordWrap(True)
        root.addWidget(hint)
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.rows_host = QtWidgets.QWidget()
        self.rows = QtWidgets.QVBoxLayout(self.rows_host)
        self.rows.setSpacing(9)
        self.rows.addStretch(1)
        self.scroll.setWidget(self.rows_host)
        root.addWidget(self.scroll, 1)
        if not self.load_existing():
            self.add_event()

    def add_event(self, data=None):
        data = data or {}
        frame = QtWidgets.QFrame()
        index = max(0, self.rows.count()-1)
        frame.setStyleSheet("QFrame{background:%s;border:1px solid #58657a;border-radius:9px;} QLabel{border:0;background:transparent;}" % self.COLORS[index % len(self.COLORS)])
        layout = QtWidgets.QGridLayout(frame)
        trigger = QtWidgets.QComboBox()
        trigger.addItems(list(self.TRIGGERS.keys()))
        action = QtWidgets.QComboBox()
        action.addItems(self.ACTIONS)
        if data.get("trigger") in self.TRIGGERS:
            trigger.setCurrentText(data["trigger"])
        if data.get("action") in self.ACTIONS:
            action.setCurrentText(data["action"])
        value = QtWidgets.QLineEdit(str(data.get("value", "Привет!")))
        value.setPlaceholderText("Текст, команда, предмет или значение")
        layout.addWidget(QtWidgets.QLabel("КОГДА"), 0, 0)
        layout.addWidget(trigger, 0, 1)
        layout.addWidget(QtWidgets.QLabel("ТОГДА"), 1, 0)
        layout.addWidget(action, 1, 1)
        layout.addWidget(value, 1, 2)
        color_btn = QtWidgets.QPushButton("Цвет")
        color_btn.clicked.connect(lambda checked=False, card=frame: self.choose_row_color(card))
        remove = QtWidgets.QPushButton("Удалить")
        remove.clicked.connect(lambda checked=False, card=frame: self.remove_event(card))
        layout.addWidget(color_btn, 0, 2)
        layout.addWidget(remove, 0, 3, 2, 1)
        frame.trigger_box = trigger
        frame.action_box = action
        frame.value_edit = value
        self.rows.insertWidget(self.rows.count()-1, frame)
        return frame

    def choose_row_color(self, frame):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor("#26364a"), self, "Выберите цвет карточки")
        if color.isValid():
            frame.setStyleSheet("QFrame{background:%s;border:1px solid #8998b0;border-radius:9px;} QLabel{border:0;background:transparent;}" % color.name())

    def remove_event(self, frame):
        self.rows.removeWidget(frame)
        frame.deleteLater()

    def event_data(self):
        result = []
        for i in range(self.rows.count()):
            frame = self.rows.itemAt(i).widget()
            if frame and hasattr(frame, "trigger_box"):
                result.append({"trigger": frame.trigger_box.currentText(),
                               "action": frame.action_box.currentText(),
                               "value": frame.value_edit.text()})
        return result

    def load_existing(self):
        path = self.project_path / "BP" / "scripts" / "events.json" if self.project_path else None
        if not path or not path.is_file():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            for item in data.get("events", []):
                self.add_event(item)
            return bool(data.get("events"))
        except Exception:
            return False

    def save_sheet(self):
        default = str(self.project_path / "BP" / "scripts" / "events.json") if self.project_path else "events.json"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить правила событий", default, "JSON (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(json.dumps({"format_version": 1, "events": self.event_data()}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            QtWidgets.QMessageBox.information(self, "Сохранено", "Правила событий сохранены.")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка сохранения", str(exc))

    def generated_script(self):
        lines = ['import { world } from "@minecraft/server";', ""]
        for index, item in enumerate(self.event_data(), 1):
            trigger = self.TRIGGERS[item["trigger"]]
            lines.append("// Правило %d: %s" % (index, item["trigger"]))
            lines.append("world.afterEvents.%s.subscribe((event) => {" % trigger)
            lines.append("  const player = event.player || event.source;")
            action, value = item["action"], item["value"]
            encoded = json.dumps(value, ensure_ascii=False)
            if action == "Отправить сообщение в чат":
                lines.append("  if (player && player.sendMessage) player.sendMessage(%s);" % encoded)
            elif action == "Выполнить команду":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % encoded)
            elif action == "Выдать предмет":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % json.dumps("give @s " + value + " 1", ensure_ascii=False))
            elif action == "Добавить эффект":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % json.dumps("effect @s " + value, ensure_ascii=False))
            elif action == "Воспроизвести звук":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % json.dumps("playsound " + value + " @s", ensure_ascii=False))
            elif action == "Создать частицу":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % json.dumps("particle " + value + " ~ ~1 ~", ensure_ascii=False))
            elif action == "Телепортировать игрока":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % json.dumps("tp @s " + value, ensure_ascii=False))
            elif action in ("Добавить тег", "Убрать тег"):
                cmd = ("tag @s add " if action == "Добавить тег" else "tag @s remove ") + value
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % json.dumps(cmd, ensure_ascii=False))
            elif action == "Изменить погоду":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % json.dumps("weather " + value, ensure_ascii=False))
            elif action == "Изменить время":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % json.dumps("time set " + value, ensure_ascii=False))
            elif action == "Показать название":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % json.dumps("title @s title " + value, ensure_ascii=False))
            elif action == "Удалить предмет из руки":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync('clear @s');")
            elif action == "Добавить опыт":
                lines.append("  if (player && player.runCommandAsync) player.runCommandAsync(%s);" % json.dumps("xp " + value + " @s", ensure_ascii=False))
            else:
                lines.append("  // Добавьте здесь свой код JavaScript: " + value.replace("\\n", " "))
            lines.append("});")
            lines.append("")
        return "\n".join(lines)

    def generate_javascript(self):
        default = str(self.project_path / "BP" / "scripts" / "main.js") if self.project_path else "main.js"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить JavaScript", default, "JavaScript (*.js)")
        if not path:
            return
        if not path.lower().endswith(".js"):
            path += ".js"
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(self.generated_script(), encoding="utf-8")
            QtWidgets.QMessageBox.information(self, "Готово", "Файл JavaScript создан. Некоторые события требуют проверки по версии Script API Minecraft.")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(exc))


class CodeEditor(QtWidgets.QPlainTextEdit):
    def __init__(self, language, parent=None):
        super().__init__(parent)
        self.language = language
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setStyleSheet("QPlainTextEdit{background:#11151d;color:#dce3ef;border:1px solid #343d4b;border-radius:6px;padding:10px;font-family:Consolas,monospace;font-size:10pt;}")
        samples = {
            "JSON": '{\n  "format_version": "1.20.0",\n  "minecraft:entity": {\n    "description": {\n      "identifier": "demo:entity"\n    }\n  }\n}',
            "JavaScript": '// Bedrock Script API example\nimport { world } from "@minecraft/server";\n\nworld.afterEvents.playerSpawn.subscribe((event) => {\n  event.player.sendMessage("Welcome!");\n});\n',
            "Molang": 'variable.speed = query.modified_move_speed;\nvariable.is_fast = variable.speed > 0.5;\n',
            "mcfunction": 'say Hello from the add-on!\neffect @a speed 5 1 true\n'
        }
        self.setPlainText(samples.get(language,""))


class LogicWorkspace(QtWidgets.QDialog):
    def __init__(self, parent=None, project_path=None):
        super().__init__(parent)
        self.setWindowTitle("Конструктор логики и кода")
        self.resize(1000,700)
        root = QtWidgets.QVBoxLayout(self)
        tabs = QtWidgets.QTabWidget()
        self.events = EventSheetEditor(self, project_path)
        tabs.addTab(self.events,"События WHEN → DO")
        self.editors = {}
        for lang in ("JSON","JavaScript","Molang","mcfunction"):
            editor = CodeEditor(lang)
            self.editors[lang] = editor
            tabs.addTab(editor,lang)
        root.addWidget(tabs,1)
        bottom = QtWidgets.QHBoxLayout()
        bottom.addStretch(1)
        save = QtWidgets.QPushButton("Сохранить код")
        save.clicked.connect(lambda: self.save_current(tabs))
        bottom.addWidget(save)
        root.addLayout(bottom)

    def save_current(self, tabs):
        widget = tabs.currentWidget()
        if widget is self.events:
            self.events.save_sheet()
            return
        language = widget.language
        extensions = {"JSON":"json","JavaScript":"js","Molang":"molang","mcfunction":"mcfunction"}
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Save "+language,"addon_code."+extensions[language],"All files (*)")
        if path:
            try:
                Path(path).write_text(widget.toPlainText(),encoding="utf-8")
                QtWidgets.QMessageBox.information(self,"Saved","Code file saved.")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self,"Ошибка сохранения",str(exc))

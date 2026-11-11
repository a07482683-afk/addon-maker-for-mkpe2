import json
from pathlib import Path
from PySide2 import QtCore, QtGui, QtWidgets


class TextureCanvas(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 420)
        self.image = QtGui.QImage(64, 64, QtGui.QImage.Format_ARGB32)
        self.image.fill(QtCore.Qt.transparent)
        self.color = QtGui.QColor("#6f83ff")
        self.tool = "Pencil"
        self.grid = True
        self.last = None
        self.undo_stack = []
        self.setMouseTracking(True)

    def snapshot(self):
        self.undo_stack.append(self.image.copy())
        if len(self.undo_stack) > 40:
            self.undo_stack.pop(0)

    def set_size(self, w, h):
        self.snapshot()
        scaled = self.image.scaled(w, h, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.FastTransformation)
        self.image = scaled
        self.update()

    def undo(self):
        if self.undo_stack:
            self.image = self.undo_stack.pop()
            self.update()

    def point_for(self, pos):
        x = int(pos.x() * self.image.width() / max(1, self.width()))
        y = int(pos.y() * self.image.height() / max(1, self.height()))
        return QtCore.QPoint(max(0, min(self.image.width()-1, x)),
                             max(0, min(self.image.height()-1, y)))

    def mousePressEvent(self, event):
        p = self.point_for(event.pos())
        if self.tool == "Eyedropper":
            self.color = self.image.pixelColor(p)
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
                if self.image.pixelColor(x,y).alpha() == 0:
                    painter.fillRect(QtCore.QRectF(x*cell_w,y*cell_h,cell_w,cell_h),
                                     QtGui.QColor("#252a35") if (x+y)%2 else QtGui.QColor("#1c2029"))
        painter.drawImage(self.rect(), self.image)
        if self.grid and cell_w >= 5 and cell_h >= 5:
            painter.setPen(QtGui.QPen(QtGui.QColor(255,255,255,35), 0))
            for x in range(w+1):
                painter.drawLine(QtCore.QPointF(x*cell_w,0), QtCore.QPointF(x*cell_w,self.height()))
            for y in range(h+1):
                painter.drawLine(QtCore.QPointF(0,y*cell_h), QtCore.QPointF(self.width(),y*cell_h))


class TextureEditor(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Texture Studio")
        self.resize(1050, 720)
        root = QtWidgets.QVBoxLayout(self)
        top = QtWidgets.QHBoxLayout()
        self.size_box = QtWidgets.QComboBox()
        for size in ("16 × 16", "32 × 32", "64 × 64", "128 × 128", "256 × 256"):
            self.size_box.addItem(size)
        self.size_box.setCurrentIndex(2)
        self.size_box.currentIndexChanged.connect(self.change_size)
        top.addWidget(QtWidgets.QLabel("Canvas size"))
        top.addWidget(self.size_box)
        self.grid_box = QtWidgets.QCheckBox("Pixel grid")
        self.grid_box.setChecked(True)
        self.grid_box.toggled.connect(self.toggle_grid)
        top.addWidget(self.grid_box)
        top.addStretch(1)
        undo = QtWidgets.QPushButton("Undo")
        undo.clicked.connect(lambda: self.canvas.undo())
        top.addWidget(undo)
        open_btn = QtWidgets.QPushButton("Open PNG")
        open_btn.clicked.connect(self.open_image)
        top.addWidget(open_btn)
        save_btn = QtWidgets.QPushButton("Export PNG")
        save_btn.clicked.connect(self.save_image)
        top.addWidget(save_btn)
        root.addLayout(top)

        body = QtWidgets.QHBoxLayout()
        tools = QtWidgets.QVBoxLayout()
        self.canvas = TextureCanvas()
        for tool in ("Pencil", "Eraser", "Fill", "Eyedropper"):
            b = QtWidgets.QPushButton(tool)
            b.clicked.connect(lambda checked=False, t=tool: self.set_tool(t))
            tools.addWidget(b)
        color_btn = QtWidgets.QPushButton("Choose color")
        color_btn.clicked.connect(self.choose_color)
        tools.addWidget(color_btn)
        self.color_preview = QtWidgets.QLabel("  ")
        self.color_preview.setFixedHeight(32)
        self.color_preview.setStyleSheet("background:#6f83ff;border:1px solid #555;border-radius:5px;")
        tools.addWidget(self.color_preview)
        tools.addStretch(1)
        body.addLayout(tools)
        body.addWidget(self.canvas, 1)
        root.addLayout(body, 1)
        self.status = QtWidgets.QLabel("Pencil • 64 × 64 • Transparent background")
        root.addWidget(self.status)

    def set_tool(self, tool):
        self.canvas.tool = tool
        self.status.setText(tool + " • %d × %d" % (self.canvas.image.width(), self.canvas.image.height()))

    def change_size(self, index):
        size = (16,32,64,128,256)[index]
        self.canvas.set_size(size, size)
        self.status.setText("Canvas resized to %d × %d" % (size,size))

    def toggle_grid(self, enabled):
        self.canvas.grid = enabled
        self.canvas.update()

    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor(self.canvas.color, self, "Texture color", QtWidgets.QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.canvas.color = color
            self.color_preview.setStyleSheet("background:%s;border:1px solid #555;border-radius:5px;" % color.name())
            self.status.setText("Color: " + color.name())

    def open_image(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open texture", "", "Images (*.png *.jpg *.bmp)")
        if path:
            image = QtGui.QImage(path)
            if not image.isNull():
                self.canvas.snapshot()
                self.canvas.image = image.convertToFormat(QtGui.QImage.Format_ARGB32)
                self.canvas.update()
                self.status.setText("Opened " + Path(path).name)

    def save_image(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export texture", "texture.png", "PNG image (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            if self.canvas.image.save(path, "PNG"):
                self.status.setText("Exported " + path)
            else:
                QtWidgets.QMessageBox.warning(self, "Export failed", "Could not save this PNG file.")


class EventSheetEditor(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QtWidgets.QVBoxLayout(self)
        bar = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Visual Event Sheet")
        title.setStyleSheet("font-size:18pt;font-weight:700;")
        bar.addWidget(title)
        bar.addStretch(1)
        add = QtWidgets.QPushButton("+ Add event")
        add.clicked.connect(self.add_event)
        bar.addWidget(add)
        save = QtWidgets.QPushButton("Save event sheet")
        save.clicked.connect(self.save_sheet)
        bar.addWidget(save)
        root.addLayout(bar)
        hint = QtWidgets.QLabel("Build logic as: WHEN condition(s) are true → DO action(s). Events are stored as editable JSON.")
        hint.setWordWrap(True)
        root.addWidget(hint)
        self.rows = QtWidgets.QVBoxLayout()
        self.rows.setSpacing(8)
        root.addLayout(self.rows)
        root.addStretch(1)
        self.add_event()

    def add_event(self):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("QFrame{background:#202631;border:1px solid #3a4352;border-radius:8px;} QLabel{border:0;}")
        layout = QtWidgets.QGridLayout(frame)
        condition = QtWidgets.QLineEdit("Player enters area")
        action = QtWidgets.QLineEdit("Show message: Hello!")
        condition.setPlaceholderText("Condition, e.g. player_interact")
        action.setPlaceholderText("Action, e.g. run_command")
        layout.addWidget(QtWidgets.QLabel("WHEN"),0,0)
        layout.addWidget(condition,0,1)
        layout.addWidget(QtWidgets.QLabel("DO"),1,0)
        layout.addWidget(action,1,1)
        remove = QtWidgets.QPushButton("Remove")
        remove.clicked.connect(lambda: self.remove_event(frame))
        layout.addWidget(remove,0,2,2,1)
        frame.condition_edit = condition
        frame.action_edit = action
        self.rows.addWidget(frame)

    def remove_event(self, frame):
        self.rows.removeWidget(frame)
        frame.deleteLater()

    def save_sheet(self):
        events = []
        for i in range(self.rows.count()):
            frame = self.rows.itemAt(i).widget()
            if frame:
                events.append({"conditions":[frame.condition_edit.text()],
                               "actions":[frame.action_edit.text()]})
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save event sheet", "events.json", "JSON (*.json)")
        if path:
            if not path.lower().endswith(".json"):
                path += ".json"
            try:
                Path(path).write_text(json.dumps({"format_version":1,"events":events},indent=2,ensure_ascii=False),encoding="utf-8")
                QtWidgets.QMessageBox.information(self,"Saved","Event sheet saved.")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self,"Save failed",str(exc))


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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logic & Code Workspace")
        self.resize(1000,700)
        root = QtWidgets.QVBoxLayout(self)
        tabs = QtWidgets.QTabWidget()
        self.events = EventSheetEditor()
        tabs.addTab(self.events,"Event Sheet")
        self.editors = {}
        for lang in ("JSON","JavaScript","Molang","mcfunction"):
            editor = CodeEditor(lang)
            self.editors[lang] = editor
            tabs.addTab(editor,lang)
        root.addWidget(tabs,1)
        bottom = QtWidgets.QHBoxLayout()
        bottom.addStretch(1)
        save = QtWidgets.QPushButton("Save current code")
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
                QtWidgets.QMessageBox.critical(self,"Save failed",str(exc))

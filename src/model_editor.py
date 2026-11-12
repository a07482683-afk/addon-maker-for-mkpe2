import json
import math
import re
from pathlib import Path
from PySide2 import QtCore, QtGui, QtWidgets


class Mesh:
    def __init__(self, vertices, faces, source, groups=None, texcoords=None):
        self.vertices = vertices
        self.faces = faces
        self.source = source
        self.groups = groups or {"root": list(range(len(faces)))}
        self.texcoords = texcoords or []


def load_obj(path):
    vertices, texcoords, faces = [], [], []
    groups = {}
    active = "root"
    with open(str(path), "r", encoding="utf-8", errors="replace") as stream:
        for raw_line in stream:
            line = raw_line.strip()
            if line.startswith("o ") or line.startswith("g "):
                active = re.sub(r"[^A-Za-z0-9_]+", "_", line[2:].strip()) or "root"
                groups.setdefault(active, [])
            elif line.startswith("v "):
                values = line.split()
                if len(values) >= 4:
                    vertices.append(tuple(float(v) for v in values[1:4]))
            elif line.startswith("vt "):
                values = line.split()
                if len(values) >= 3:
                    texcoords.append(tuple(float(v) for v in values[1:3]))
            elif line.startswith("f "):
                corners = []
                for token in line.split()[1:]:
                    parts = token.split("/")
                    vi = int(parts[0])
                    vi = vi - 1 if vi > 0 else len(vertices) + vi
                    ti = None
                    if len(parts) > 1 and parts[1]:
                        ti = int(parts[1])
                        ti = ti - 1 if ti > 0 else len(texcoords) + ti
                    if vi < 0 or vi >= len(vertices):
                        raise ValueError("OBJ contains an invalid vertex index.")
                    corners.append((vi, ti))
                if len(corners) >= 3:
                    for i in range(1, len(corners) - 1):
                        tri = (corners[0], corners[i], corners[i + 1])
                        face_index = len(faces)
                        faces.append(tuple(c[0] for c in tri))
                        groups.setdefault(active, []).append(face_index)
    groups = {name: ids for name, ids in groups.items() if ids}
    if not vertices or not faces:
        raise ValueError("OBJ file contains no readable polygon mesh.")
    return Mesh(vertices, faces, str(path), groups, texcoords)


def load_ascii_fbx(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    if "Kaydara FBX Binary" in text[:32]:
        raise ValueError("Binary FBX is not supported. Export as ASCII FBX or OBJ.")
    vm = re.search(r"Vertices\s*:\s*\*\s*\d+\s*\{\s*a\s*:\s*([^}]*)\}", text, re.S)
    pm = re.search(r"PolygonVertexIndex\s*:\s*\*\s*\d+\s*\{\s*a\s*:\s*([^}]*)\}", text, re.S)
    if not vm or not pm:
        raise ValueError("Could not read FBX mesh arrays. Export as ASCII FBX or OBJ.")
    numbers = [float(x) for x in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", vm.group(1))]
    if len(numbers) < 9 or len(numbers) % 3:
        raise ValueError("FBX vertex array is invalid.")
    vertices = [tuple(numbers[i:i + 3]) for i in range(0, len(numbers), 3)]
    indices = [int(x) for x in re.findall(r"-?\d+", pm.group(1))]
    faces, face = [], []
    for value in indices:
        index = -value - 1 if value < 0 else value
        if index < 0 or index >= len(vertices):
            raise ValueError("FBX polygon index is out of range.")
        face.append(index)
        if value < 0:
            if len(face) >= 3:
                for i in range(1, len(face) - 1):
                    faces.append((face[0], face[i], face[i + 1]))
            face = []
    if not faces:
        raise ValueError("FBX file contains no readable polygons.")
    return Mesh(vertices, faces, str(path))


def import_mesh(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".obj":
        return load_obj(path)
    if suffix == ".fbx":
        return load_ascii_fbx(path)
    raise ValueError("Choose an OBJ or FBX file.")


def _safe_bone_name(name, index):
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_") or "part"
    if cleaned[0].isdigit():
        cleaned = "part_" + cleaned
    return (cleaned[:40] + "_" + str(index))[:48]


def bedrock_geometry(mesh, identifier, texture_width=64, texture_height=64):
    all_vertices = mesh.vertices
    mins = [min(v[i] for v in all_vertices) for i in range(3)]
    maxs = [max(v[i] for v in all_vertices) for i in range(3)]
    spans = [maxs[i] - mins[i] for i in range(3)]
    scale = 16.0 / (max(spans) or 1.0)
    safe_id = identifier if identifier.startswith("geometry.") else "geometry." + identifier
    bones = []
    group_items = list(mesh.groups.items()) if mesh.groups else [("root", list(range(len(mesh.faces))))]
    for index, (group_name, face_ids) in enumerate(group_items):
        used = sorted({vertex_id for face_id in face_ids for vertex_id in mesh.faces[face_id]})
        if not used:
            continue
        part_min = [min(mesh.vertices[v][i] for v in used) for i in range(3)]
        part_max = [max(mesh.vertices[v][i] for v in used) for i in range(3)]
        origin = [round((part_min[i] - mins[i]) * scale - 8.0, 4) for i in range(3)]
        size = [max(0.01, round((part_max[i] - part_min[i]) * scale, 4)) for i in range(3)]
        bones.append({
            "name": _safe_bone_name(group_name, index),
            "pivot": [round(origin[0] + size[0] / 2, 4), round(origin[1], 4), round(origin[2] + size[2] / 2, 4)],
            "cubes": [{
                "origin": origin,
                "size": size,
                "uv": [0, 0]
            }]
        })
    if not bones:
        raise ValueError("No usable mesh groups were found.")
    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": safe_id,
                "texture_width": int(texture_width),
                "texture_height": int(texture_height),
                "visible_bounds_width": 2.0,
                "visible_bounds_height": 2.0,
                "visible_bounds_offset": [0, 0.5, 0]
            },
            "bones": bones
        }]
    }


def bedrock_animation(identifier, duration, axis, angle):
    safe_id = identifier if identifier.startswith("animation.") else "animation." + identifier
    rotation = [0.0, 0.0, 0.0]
    rotation[{"X": 0, "Y": 1, "Z": 2}[axis]] = float(angle)
    return {
        "format_version": "1.8.0",
        "animations": {
            safe_id: {
                "loop": True,
                "animation_length": float(duration),
                "bones": {
                    "root": {
                        "rotation": {
                            "0.0": [0, 0, 0],
                            str(float(duration)): rotation
                        }
                    }
                }
            }
        }
    }


class MeshView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 360)
        self.mesh = None
        self.yaw, self.pitch, self.zoom = -35.0, 20.0, 1.0
        self.last_pos = None
        self.setStyleSheet("background:#11151d;border:1px solid #343b4b;border-radius:8px;")

    def set_mesh(self, mesh):
        self.mesh = mesh
        self.update()

    def reset_view(self):
        self.yaw, self.pitch, self.zoom = -35.0, 20.0, 1.0
        self.update()

    def game_view(self):
        self.yaw, self.pitch, self.zoom = -45.0, 28.0, 1.15
        self.update()

    def mousePressEvent(self, event):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_pos is not None and event.buttons() & QtCore.Qt.LeftButton:
            delta = event.pos() - self.last_pos
            self.yaw += delta.x() * 0.8
            self.pitch = max(-89, min(89, self.pitch + delta.y() * 0.8))
            self.last_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.last_pos = None

    def wheelEvent(self, event):
        self.zoom = max(0.15, min(8.0, self.zoom * (1.12 if event.angleDelta().y() > 0 else 0.89)))
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("#11151d"))
        if not self.mesh:
            painter.setPen(QtGui.QColor("#9aa5b8"))
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, "Import OBJ or ASCII FBX\nDrag to rotate • Wheel to zoom")
            return
        verts = self.mesh.vertices
        center = [sum(v[i] for v in verts) / len(verts) for i in range(3)]
        radius = max((sum((v[i] - center[i]) ** 2 for i in range(3)) ** 0.5 for v in verts), default=1) or 1
        yaw, pitch = math.radians(self.yaw), math.radians(self.pitch)
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        scale = min(self.width(), self.height()) * 0.38 * self.zoom / radius
        projected = []
        for v in verts:
            x, y, z = [v[i] - center[i] for i in range(3)]
            rx, rz = x * cy - z * sy, x * sy + z * cy
            ry, rz2 = y * cp - rz * sp, y * sp + rz * cp
            projected.append((self.width() / 2 + rx * scale, self.height() / 2 - ry * scale, rz2))
        triangles = []
        for face in self.mesh.faces:
            pts = [projected[i] for i in face]
            triangles.append((sum(p[2] for p in pts) / 3, pts))
        triangles.sort(key=lambda item: item[0])
        for depth, pts in triangles:
            poly = QtGui.QPolygonF([QtCore.QPointF(p[0], p[1]) for p in pts])
            shade = max(65, min(190, int(125 + depth * 2)))
            painter.setBrush(QtGui.QColor(shade, min(255, shade + 8), min(255, shade + 24)))
            painter.setPen(QtGui.QPen(QtGui.QColor("#202a3a"), 1))
            painter.drawPolygon(poly)
        painter.setPen(QtGui.QColor("#aab6c8"))
        painter.drawText(12, 22, "Faces: %d   Vertices: %d   Parts: %d" % (len(self.mesh.faces), len(verts), len(self.mesh.groups)))


class ModelWorkspace(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("3D-редактор — предпросмотр Minecraft")
        self.resize(1080, 760)
        self.mesh = None
        root = QtWidgets.QVBoxLayout(self)
        bar = QtWidgets.QHBoxLayout()
        self.path_label = QtWidgets.QLabel("Модель ещё не загружена")
        button = QtWidgets.QPushButton("＋ Импортировать OBJ / FBX…")
        button.clicked.connect(self.choose_model)
        game_view = QtWidgets.QPushButton("Вид как в Minecraft")
        game_view.clicked.connect(lambda: self.view.game_view())
        reset_view = QtWidgets.QPushButton("Сбросить поворот")
        reset_view.clicked.connect(lambda: self.view.reset_view())
        bar.addWidget(button)
        bar.addWidget(game_view)
        bar.addWidget(reset_view)
        bar.addWidget(self.path_label, 1)
        root.addLayout(bar)
        self.view = MeshView()
        root.addWidget(self.view, 1)
        preview_bar = QtWidgets.QHBoxLayout()
        preview_note = QtWidgets.QLabel("ЛКМ — вращать модель • Колесо — приближать и отдалять")
        preview_note.setStyleSheet("color:#aab6c8;")
        preview_bar.addWidget(preview_note)
        preview_bar.addStretch(1)
        snapshot = QtWidgets.QPushButton("Сохранить снимок 3D-вида…")
        snapshot.clicked.connect(self.save_preview)
        preview_bar.addWidget(snapshot)
        root.addLayout(preview_bar)
        geometry_box = QtWidgets.QGroupBox("Геометрия Minecraft Bedrock")
        geometry_form = QtWidgets.QFormLayout(geometry_box)
        self.geometry_id = QtWidgets.QLineEdit("geometry.custom_model")
        self.texture_width = QtWidgets.QSpinBox()
        self.texture_width.setRange(16, 1024)
        self.texture_width.setValue(64)
        self.texture_height = QtWidgets.QSpinBox()
        self.texture_height.setRange(16, 1024)
        self.texture_height.setValue(64)
        geometry_form.addRow("Идентификатор геометрии", self.geometry_id)
        texture_row = QtWidgets.QHBoxLayout()
        texture_row.addWidget(self.texture_width)
        texture_row.addWidget(QtWidgets.QLabel("×"))
        texture_row.addWidget(self.texture_height)
        geometry_form.addRow("Размер текстуры", texture_row)
        save_geometry = QtWidgets.QPushButton("Экспортировать Geometry JSON…")
        save_geometry.clicked.connect(self.save_geometry)
        geometry_form.addRow(save_geometry)
        root.addWidget(geometry_box)
        animation_box = QtWidgets.QGroupBox("Простая анимация и ключевые кадры")
        animation_form = QtWidgets.QFormLayout(animation_box)
        self.animation_id = QtWidgets.QLineEdit("animation.custom_model.rotate")
        self.duration = QtWidgets.QDoubleSpinBox()
        self.duration.setRange(0.1, 120.0)
        self.duration.setValue(2.0)
        self.axis = QtWidgets.QComboBox()
        self.axis.addItems(["X", "Y", "Z"])
        self.angle = QtWidgets.QDoubleSpinBox()
        self.angle.setRange(-360.0, 360.0)
        self.angle.setValue(30.0)
        animation_form.addRow("Идентификатор анимации", self.animation_id)
        animation_form.addRow("Длительность (секунды)", self.duration)
        animation_form.addRow("Ось вращения", self.axis)
        animation_form.addRow("Угол поворота (градусы)", self.angle)
        save_animation = QtWidgets.QPushButton("Экспортировать Animation JSON…")
        save_animation.clicked.connect(self.save_animation)
        animation_form.addRow(save_animation)
        root.addWidget(animation_box)
        note = QtWidgets.QLabel("OBJ groups/objects become separate Bedrock bones. Each part is currently represented by a fitted cuboid; OBJ UV coordinates are read but not yet transferred to individual cube faces. ASCII FBX is supported; binary FBX is not.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#e6c27a;")
        root.addWidget(note)

    def save_preview(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить снимок 3D-модели", "model-preview.png", "PNG (*.png)")
        if filename:
            if not filename.lower().endswith(".png"):
                filename += ".png"
            if not self.view.grab().save(filename, "PNG"):
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удалось сохранить снимок.")
            else:
                QtWidgets.QMessageBox.information(self, "Готово", "Снимок сохранён: " + filename)

    def choose_model(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Импортировать 3D-модель", "", "3D-модели (*.obj *.fbx)")
        if not filename:
            return
        try:
            self.mesh = import_mesh(filename)
            self.view.set_mesh(self.mesh)
            self.path_label.setText(Path(filename).name)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка импорта", str(exc))

    def save_geometry(self):
        if not self.mesh:
            QtWidgets.QMessageBox.warning(self, "Нет модели", "Сначала импортируйте модель.")
            return
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить геометрию Bedrock", "geometry.custom_model.json", "JSON files (*.json)")
        if not filename:
            return
        try:
            data = bedrock_geometry(self.mesh, self.geometry_id.text().strip() or "geometry.custom_model",
                                    self.texture_width.value(), self.texture_height.value())
            Path(filename).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            QtWidgets.QMessageBox.information(self, "Сохранено", "Bedrock geometry exported to:\n" + filename)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка экспорта", str(exc))

    def save_animation(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить анимацию Bedrock", "animation.custom_model.json", "JSON files (*.json)")
        if not filename:
            return
        try:
            data = bedrock_animation(self.animation_id.text().strip() or "animation.custom_model.rotate",
                                     self.duration.value(), self.axis.currentText(), self.angle.value())
            Path(filename).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            QtWidgets.QMessageBox.information(self, "Сохранено", "Starter animation JSON exported to:\n" + filename)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Ошибка экспорта", str(exc))

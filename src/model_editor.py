import json
import math
import re
import shutil
from pathlib import Path
from PySide2 import QtCore, QtGui, QtWidgets


class Mesh:
    def __init__(self, vertices, faces, source, groups=None, texcoords=None, face_uvs=None):
        self.vertices = vertices
        self.faces = faces
        self.source = source
        self.groups = groups or {"root": list(range(len(faces)))}
        self.texcoords = texcoords or []
        self.face_uvs = face_uvs or [None] * len(faces)


def load_obj(path):
    vertices, texcoords, faces, face_uvs = [], [], [], []
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
                        face_uvs.append(tuple(texcoords[c[1]] if c[1] is not None and 0 <= c[1] < len(texcoords) else None for c in tri))
                        groups.setdefault(active, []).append(face_index)
    groups = {name: ids for name, ids in groups.items() if ids}
    if not vertices or not faces:
        raise ValueError("OBJ file contains no readable polygon mesh.")
    return Mesh(vertices, faces, str(path), groups, texcoords, face_uvs)


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
    return Mesh(vertices, faces, str(path), face_uvs=[None] * len(faces))


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
    mins = [min(v[i] for v in mesh.vertices) for i in range(3)]
    maxs = [max(v[i] for v in mesh.vertices) for i in range(3)]
    scale = 16.0 / (max(maxs[i]-mins[i] for i in range(3)) or 1.0)
    safe_id = identifier if identifier.startswith("geometry.") else "geometry." + identifier
    bones = []
    for index, (group_name, face_ids) in enumerate((list(mesh.groups.items()) or [("root", list(range(len(mesh.faces))))])):
        vertex_map, positions, uvs, normals, polygons = {}, [], [], [], []
        for face_id in face_ids:
            face = mesh.faces[face_id]
            uv_corners = mesh.face_uvs[face_id] if face_id < len(mesh.face_uvs) else None
            a, b, c = [mesh.vertices[v] for v in face]
            ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
            vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
            nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
            length = math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0
            normal = (nx/length, ny/length, nz/length)
            polygon = []
            for corner, vertex_id in enumerate(face):
                uv = uv_corners[corner] if uv_corners and uv_corners[corner] is not None else (0.0, 0.0)
                key = (vertex_id, round(uv[0], 7), round(uv[1], 7))
                if key not in vertex_map:
                    v = mesh.vertices[vertex_id]
                    vertex_map[key] = len(positions)
                    positions.append([round((v[i]-mins[i])*scale-8.0, 5) for i in range(3)])
                    uvs.append([round(float(uv[0]), 6), round(1.0-float(uv[1]), 6)])
                    normals.append([round(x, 6) for x in normal])
                polygon.append(vertex_map[key])
            polygons.append(polygon + [-1])
        if positions:
            bones.append({"name": _safe_bone_name(group_name, index), "pivot": [0, 0, 0],
                          "poly_mesh": {"normalized_uvs": True, "positions": positions,
                                        "normals": normals, "uvs": uvs, "polys": polygons}})
    if not bones:
        raise ValueError("Не удалось создать геометрию: в модели нет полигонов.")
    return {"format_version": "1.12.0", "minecraft:geometry": [{
        "description": {"identifier": safe_id, "texture_width": int(texture_width),
                        "texture_height": int(texture_height), "visible_bounds_width": 2.0,
                        "visible_bounds_height": 2.0, "visible_bounds_offset": [0, 0.5, 0]},
        "bones": bones}]}

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
        self.wireframe = True
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
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, "Импортируйте OBJ или ASCII FBX\nЛКМ — вращение • Колесо — масштаб")
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
            edge = QtGui.QColor("#202a3a") if self.wireframe else QtGui.QColor(shade, min(255, shade + 8), min(255, shade + 24))
            painter.setPen(QtGui.QPen(edge, 1 if self.wireframe else 0))
            painter.drawPolygon(poly)
        painter.setPen(QtGui.QColor("#aab6c8"))
        painter.drawText(12, 22, "Faces: %d   Vertices: %d   Parts: %d" % (len(self.mesh.faces), len(verts), len(self.mesh.groups)))


class ModelWorkspace(QtWidgets.QDialog):
    def __init__(self, parent=None, project_path=None):
        super().__init__(parent)
        self.setWindowTitle("3D-редактор — предпросмотр Minecraft")
        self.resize(1080, 760)
        self.mesh = None
        self.project_path = Path(project_path) if project_path else None
        self.model_file = None
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
        wire_button = QtWidgets.QPushButton("Сетка полигонов: вкл / выкл")
        wire_button.clicked.connect(self.toggle_wireframe)
        root.addWidget(wire_button)
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
        note = QtWidgets.QLabel("OBJ-группы становятся отдельными костями, а треугольники и UV-координаты переносятся в poly_mesh. FBX пока импортируется без UV; бинарный FBX не поддерживается.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#e6c27a;")
        root.addWidget(note)

    def toggle_wireframe(self):
        self.view.wireframe = not self.view.wireframe
        self.view.update()

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
            source = Path(filename)
            if self.project_path:
                model_dir = self.project_path / "Models"
                model_dir.mkdir(parents=True, exist_ok=True)
                saved = model_dir / source.name
                if source.resolve() != saved.resolve():
                    shutil.copy2(str(source), str(saved))
                self.model_file = saved
            else:
                self.model_file = source
            self.mesh = import_mesh(str(self.model_file))
            self.view.set_mesh(self.mesh)
            self.path_label.setText(self.model_file.name)
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

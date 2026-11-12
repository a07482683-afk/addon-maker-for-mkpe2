import json
import math
import re
from pathlib import Path
from PySide2 import QtCore, QtGui, QtWidgets


class Mesh:
    def __init__(self, vertices, faces, source):
        self.vertices, self.faces, self.source = vertices, faces, source


def load_obj(path):
    vertices, faces = [], []
    with open(str(path), "r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            line = line.strip()
            if line.startswith("v "):
                values = line.split()
                if len(values) >= 4:
                    vertices.append(tuple(float(v) for v in values[1:4]))
            elif line.startswith("f "):
                face = []
                for token in line.split()[1:]:
                    raw = token.split("/")[0]
                    if raw:
                        index = int(raw)
                        face.append(index - 1 if index > 0 else len(vertices) + index)
                if len(face) >= 3 and all(0 <= i < len(vertices) for i in face):
                    for i in range(1, len(face) - 1):
                        faces.append((face[0], face[i], face[i + 1]))
    if not vertices or not faces:
        raise ValueError("OBJ file contains no readable polygon mesh.")
    return Mesh(vertices, faces, str(path))


def load_ascii_fbx(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    if "Kaydara FBX Binary" in text[:32]:
        raise ValueError("Binary FBX is not supported. Export as ASCII FBX or OBJ.")
    vm = re.search(r"Vertices\s*:\s*\*\s*\d+\s*\{\s*a\s*:\s*([^}]*)\}", text, re.S)
    pm = re.search(r"PolygonVertexIndex\s*:\s*\*\s*\d+\s*\{\s*a\s*:\s*([^}]*)\}", text, re.S)
    if not vm or not pm:
        raise ValueError("Could not read FBX mesh arrays. Try exporting as ASCII FBX.")
    numbers = [float(x) for x in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", vm.group(1))]
    if len(numbers) < 9 or len(numbers) % 3:
        raise ValueError("FBX vertex array is invalid.")
    vertices = [tuple(numbers[i:i+3]) for i in range(0, len(numbers), 3)]
    indices = [int(x) for x in re.findall(r"-?\d+", pm.group(1))]
    faces, face = [], []
    for value in indices:
        index = -value - 1 if value < 0 else value
        if index < 0 or index >= len(vertices):
            raise ValueError("FBX polygon index is out of range.")
        face.append(index)
        if value < 0:
            if len(face) >= 3:
                for i in range(1, len(face)-1):
                    faces.append((face[0], face[i], face[i+1]))
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


def bedrock_geometry(mesh, identifier):
    mins = [min(v[i] for v in mesh.vertices) for i in range(3)]
    maxs = [max(v[i] for v in mesh.vertices) for i in range(3)]
    spans = [maxs[i] - mins[i] for i in range(3)]
    scale = 16.0 / (max(spans) or 1.0)
    origin = [round(mins[i] * scale, 4) for i in range(3)]
    size = [max(0.01, round(spans[i] * scale, 4)) for i in range(3)]
    safe_id = identifier if identifier.startswith("geometry.") else "geometry." + identifier
    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": safe_id,
                "texture_width": 64,
                "texture_height": 64,
                "visible_bounds_width": 2.0,
                "visible_bounds_height": 2.0,
                "visible_bounds_offset": [0, 0.5, 0]
            },
            "bones": [{
                "name": "root", "pivot": [0, 0, 0],
                "cubes": [{"origin": origin, "size": size, "uv": [0, 0]}]
            }]
        }]
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
        radius = max((sum((v[i]-center[i])**2 for i in range(3))**0.5 for v in verts), default=1) or 1
        yaw, pitch = math.radians(self.yaw), math.radians(self.pitch)
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        scale = min(self.width(), self.height()) * 0.38 * self.zoom / radius
        projected = []
        for v in verts:
            x, y, z = [v[i]-center[i] for i in range(3)]
            rx, rz = x*cy-z*sy, x*sy+z*cy
            ry, rz2 = y*cp-rz*sp, y*sp+rz*cp
            projected.append((self.width()/2+rx*scale, self.height()/2-ry*scale, rz2))
        triangles = []
        for face in self.mesh.faces:
            pts = [projected[i] for i in face]
            triangles.append((sum(p[2] for p in pts)/3, pts))
        triangles.sort(key=lambda item: item[0])
        for depth, pts in triangles:
            poly = QtGui.QPolygonF([QtCore.QPointF(p[0], p[1]) for p in pts])
            shade = max(65, min(190, int(125 + depth*2)))
            painter.setBrush(QtGui.QColor(shade, min(255, shade+8), min(255, shade+24)))
            painter.setPen(QtGui.QPen(QtGui.QColor("#202a3a"), 1))
            painter.drawPolygon(poly)
        painter.setPen(QtGui.QColor("#aab6c8"))
        painter.drawText(12, 22, "Faces: %d   Vertices: %d" % (len(self.mesh.faces), len(verts)))


class ModelWorkspace(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("3D Models & Bedrock Geometry")
        self.resize(1080, 700)
        self.mesh = None
        root = QtWidgets.QVBoxLayout(self)
        bar = QtWidgets.QHBoxLayout()
        self.path_label = QtWidgets.QLabel("No model imported")
        button = QtWidgets.QPushButton("Import OBJ / FBX…")
        button.clicked.connect(self.choose_model)
        bar.addWidget(button)
        bar.addWidget(self.path_label, 1)
        root.addLayout(bar)
        self.view = MeshView()
        root.addWidget(self.view, 1)
        controls = QtWidgets.QHBoxLayout()
        self.geometry_id = QtWidgets.QLineEdit("geometry.custom_model")
        self.geometry_id.setMinimumWidth(220)
        controls.addWidget(QtWidgets.QLabel("Geometry identifier"))
        controls.addWidget(self.geometry_id)
        save = QtWidgets.QPushButton("Save Bedrock geometry JSON…")
        save.clicked.connect(self.save_geometry)
        controls.addWidget(save)
        root.addLayout(controls)
        note = QtWidgets.QLabel("Preview shows the imported mesh. Current Bedrock export creates a normalized root-bone bounding cube proxy, not a triangle-to-cube mesh conversion.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#e6c27a;")
        root.addWidget(note)

    def choose_model(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import 3D model", "", "3D models (*.obj *.fbx)")
        if not filename:
            return
        try:
            self.mesh = import_mesh(filename)
            self.view.set_mesh(self.mesh)
            self.path_label.setText(Path(filename).name)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Import failed", str(exc))

    def save_geometry(self):
        if not self.mesh:
            QtWidgets.QMessageBox.warning(self, "No model", "Import a model first.")
            return
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Bedrock geometry", "geometry.custom_model.json", "JSON files (*.json)")
        if not filename:
            return
        try:
            data = bedrock_geometry(self.mesh, self.geometry_id.text().strip() or "geometry.custom_model")
            Path(filename).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            QtWidgets.QMessageBox.information(self, "Saved", "Starter Bedrock geometry saved to:\n" + filename)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(exc))

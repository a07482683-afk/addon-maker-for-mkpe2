import json
import sys
import uuid
from pathlib import Path
from PySide2 import QtCore, QtGui, QtWidgets
from editors import TextureEditor, LogicWorkspace

APP_NAME = "Addon Maker for MCPE"
APP_VERSION = "0.1.0"

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def manifest(name, description, pack_type):
    return {
        "format_version": 2,
        "header": {
            "name": name, "description": description, "uuid": str(uuid.uuid4()),
            "version": [1, 0, 0], "min_engine_version": [1, 20, 0]
        },
        "modules": [{
            "type": "data" if pack_type == "BP" else "resources",
            "uuid": str(uuid.uuid4()), "version": [1, 0, 0]
        }]
    }

def create_project(location, name, description):
    safe = "".join(c for c in name if c.isalnum() or c in " -_").strip()
    if not safe:
        raise ValueError("Project name must contain letters or numbers.")
    project = Path(location) / safe
    if project.exists():
        raise FileExistsError("That project folder already exists.")
    bp, rp = project / "BP", project / "RP"
    bp.mkdir(parents=True)
    rp.mkdir(parents=True)
    write_json(bp / "manifest.json", manifest(safe + " BP", description, "BP"))
    write_json(rp / "manifest.json", manifest(safe + " RP", description, "RP"))
    (project / "README.txt").write_text(
        safe + "\nBehavior Pack: BP/\nResource Pack: RP/\nCreated with " +
        APP_NAME + " " + APP_VERSION + "\n", encoding="utf-8")
    return project

class ProjectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create a new add-on")
        self.setMinimumWidth(460)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.name = QtWidgets.QLineEdit("My First Addon")
        self.description = QtWidgets.QLineEdit("A custom Minecraft Bedrock add-on")
        self.location = QtWidgets.QLineEdit(str(Path.home() / "Documents" / "MCPE Addons"))
        browse = QtWidgets.QPushButton("Browse...")
        browse.clicked.connect(self.browse)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.location, 1)
        row.addWidget(browse)
        form.addRow("Project name", self.name)
        form.addRow("Description", self.description)
        form.addRow("Save location", row)
        layout.addLayout(form)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText('Create')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose project location")
        if folder:
            self.location.setText(folder)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME + " • " + APP_VERSION)
        self.resize(1180, 760)
        self.setMinimumSize(900, 600)
        self.setStyleSheet("""
        QWidget { background:#17191f; color:#e7eaf0; font-family:Segoe UI,Arial; font-size:10pt; }
        QFrame#Sidebar { background:#111319; border-right:1px solid #292d37; }
        QLabel#Brand { color:#8b9cff; font-size:17pt; font-weight:700; }
        QLabel#Muted { color:#9299a8; }
        QLabel#PageTitle { font-size:25pt; font-weight:700; }
        QFrame#Panel,QFrame#Tile { background:#20232c; border:1px solid #303541; border-radius:12px; }
        QPushButton { background:#303644; border:1px solid #41495a; border-radius:8px; padding:10px 14px; }
        QPushButton:hover { background:#3a4354; border-color:#7185ff; }
        QPushButton#Primary { background:#6578f5; border:0; color:white; font-weight:600; }
        QPushButton#Nav { text-align:left; background:transparent; border:0; padding:11px; color:#b9c0ce; }
        QPushButton#Nav:hover { background:#242936; color:white; }
        QLineEdit { background:#14171e; border:1px solid #3b4250; border-radius:7px; padding:9px; }
        QStatusBar { color:#aab1bf; background:#111319; }
        """)
        self.build_ui()

    def build_ui(self):
        central = QtWidgets.QWidget()
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(225)
        side = QtWidgets.QVBoxLayout(sidebar)
        side.setContentsMargins(18, 24, 18, 18)
        brand = QtWidgets.QLabel("◆  ADDON MAKER")
        brand.setObjectName("Brand")
        side.addWidget(brand)
        side.addSpacing(28)
        for label in ["Dashboard", "My Projects", "Content Editors", "Texture Studio", "Logic & Code", "3D Workspace", "Export"]:
            button = QtWidgets.QPushButton(label)
            button.setObjectName("Nav")
            button.clicked.connect(lambda checked=False, n=label: self.show_placeholder(n))
            side.addWidget(button)
        side.addStretch(1)
        version = QtWidgets.QLabel("MCPE / Bedrock Edition\nVersion " + APP_VERSION)
        version.setObjectName("Muted")
        side.addWidget(version)

        content = QtWidgets.QWidget()
        page = QtWidgets.QVBoxLayout(content)
        page.setContentsMargins(32, 28, 32, 24)
        page.setSpacing(18)
        top = QtWidgets.QHBoxLayout()
        headings = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("Dashboard")
        title.setObjectName("PageTitle")
        subtitle = QtWidgets.QLabel("Create, organize and export Minecraft Bedrock content.")
        subtitle.setObjectName("Muted")
        headings.addWidget(title)
        headings.addWidget(subtitle)
        top.addLayout(headings)
        top.addStretch(1)
        create = QtWidgets.QPushButton("+  New Project")
        create.setObjectName("Primary")
        create.clicked.connect(self.new_project)
        top.addWidget(create)
        page.addLayout(top)

        welcome = QtWidgets.QFrame()
        welcome.setObjectName("Panel")
        wl = QtWidgets.QHBoxLayout(welcome)
        wl.setContentsMargins(24, 20, 24, 20)
        texts = QtWidgets.QVBoxLayout()
        wt = QtWidgets.QLabel("Your next Bedrock creation starts here")
        wt.setStyleSheet("font-size:17pt;font-weight:650;")
        wd = QtWidgets.QLabel("Start with linked Behavior Pack and Resource Pack folders.")
        wd.setObjectName("Muted")
        texts.addWidget(wt)
        texts.addWidget(wd)
        wl.addLayout(texts, 1)
        quick = QtWidgets.QPushButton("Create project")
        quick.setObjectName("Primary")
        quick.clicked.connect(self.new_project)
        wl.addWidget(quick)
        page.addWidget(welcome)

        section = QtWidgets.QLabel("CONTENT WORKSPACE")
        section.setObjectName("Muted")
        section.setStyleSheet("font-weight:700;letter-spacing:1px;")
        page.addWidget(section)
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(14)
        tiles = [
            ("▦", "Items & Materials", "Item definitions and properties"),
            ("⬡", "Armor & Wearables", "Protection, durability and visuals"),
            ("▧", "Blocks", "Block properties and geometry"),
            ("⌂", "Entities", "Entity behavior and components"),
            ("◈", "Structures & Biomes", "World generation configuration"),
            ("✧", "Models & Animations", "3D assets and keyframes"),
            ("▤", "Texture Studio", "Pixel-art editor with PNG export"),
            ("⚙", "Event Sheet & Code", "Visual events plus JSON, JS, Molang and functions")
        ]
        for i, (symbol, name, detail) in enumerate(tiles):
            tile = QtWidgets.QFrame()
            tile.setObjectName("Tile")
            tl = QtWidgets.QVBoxLayout(tile)
            tl.setContentsMargins(18, 16, 18, 16)
            icon = QtWidgets.QLabel(symbol)
            icon.setStyleSheet("font-size:23pt;color:#8b9cff;")
            heading = QtWidgets.QLabel(name)
            heading.setStyleSheet("font-size:12pt;font-weight:650;")
            desc = QtWidgets.QLabel(detail)
            desc.setObjectName("Muted")
            action = QtWidgets.QPushButton("Open editor  →")
            action.clicked.connect(lambda checked=False, n=name: self.open_editor(n))
            tl.addWidget(icon)
            tl.addWidget(heading)
            tl.addWidget(desc)
            tl.addStretch(1)
            tl.addWidget(action)
            grid.addWidget(tile, i // 3, i % 3)
        page.addLayout(grid)

        panel = QtWidgets.QFrame()
        panel.setObjectName("Panel")
        pl = QtWidgets.QVBoxLayout(panel)
        pl.setContentsMargins(18, 14, 18, 14)
        recent = QtWidgets.QLabel("Recent project")
        recent.setStyleSheet("font-weight:650;font-size:12pt;")
        self.project_label = QtWidgets.QLabel("No project opened yet")
        self.project_label.setObjectName("Muted")
        pl.addWidget(recent)
        pl.addWidget(self.project_label)
        page.addWidget(panel)
        page.addStretch(1)
        root.addWidget(sidebar)
        root.addWidget(content, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready • Create a project to get started")

    def new_project(self):
        dialog = ProjectDialog(self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        name = dialog.name.text().strip()
        description = dialog.description.text().strip() or name
        location = dialog.location.text().strip()
        if not name or not location:
            QtWidgets.QMessageBox.warning(self, "Missing information", "Enter a project name and save location.")
            return
        try:
            project = create_project(location, name, description)
            self.project_label.setText(str(project))
            self.statusBar().showMessage("Project created successfully")
            QtWidgets.QMessageBox.information(self, "Project created",
                "Your project is ready!\n\n" + str(project) + "\n\nFolders created: BP and RP.")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Could not create project", str(exc))

    def open_editor(self, name):
        if name == "Texture Studio":
            TextureEditor(self).exec_()
            return
        if name in ("Event Sheet & Code", "Logic & Code"):
            LogicWorkspace(self).exec_()
            return
        self.show_placeholder(name)

    def show_placeholder(self, name):
        if name == "Dashboard":
            self.statusBar().showMessage("Dashboard")
            return
        QtWidgets.QMessageBox.information(self, name,
            name + " is planned for a later phase. The Texture Studio and Logic & Code workspace are available now.")

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())

# Addon Maker for MCPE

A desktop GUI for creating Minecraft Bedrock Edition add-on projects.

## Current features

- Dark desktop dashboard and project generator.
- Creates linked Behavior Pack (BP) and Resource Pack (RP) folders with unique starter manifests.
- Texture Studio: pixel canvas, 16/32/64/128/256 presets, pencil, eraser, flood fill, eyedropper, color picker with alpha, pixel grid, undo, PNG import and export.
- Visual Event Sheet: add/remove event rows using the Construct-style WHEN → DO workflow and save them as JSON.
- Code workspace: editable and saveable starter files for Bedrock JSON, JavaScript Script API, Molang and mcfunction.
- Windows x64 build workflow via GitHub Actions.

The visual event sheet is a beginner-friendly authoring layer; it does not yet compile every event into a working Bedrock Script API implementation. The code tabs are available for direct authoring.

## Planned next phases

- Live Bedrock texture atlas/project integration and layers.
- Item, armor, block and entity editors.
- Bedrock geometry preview and OBJ/FBX model import.
- Animation timeline and fitting tools.
- Pack validation and .mcpack / .mcaddon export.
- Event-to-code generation and expanded event/action libraries.

## Windows 7 compatibility target

The project is pinned to Python 3.8.10 and PySide2 5.15.2.1 as a legacy Windows target. The produced executable still needs testing on a clean Windows 7 SP1 x64 machine. If Windows reports a missing runtime DLL, the Microsoft Visual C++ 2015-2019 x64 runtime may be required.

## Run from source

    py -3.8 -m pip install -r requirements.txt
    py -3.8 src\main.py

## Build locally

    py -3.8 -m PyInstaller --noconfirm --clean --windowed --name AddonMaker --collect-all PySide2 src\main.py

The executable is created under dist\AddonMaker\AddonMaker.exe.

## Build with GitHub Actions

Open the repository Actions tab, select Build Addon Maker for MCPE, choose branch phase2-texture-events, and run the workflow. Download the AddonMaker-Windows-x64 artifact from the completed run.

This is an unofficial community tool and is not affiliated with Mojang or Microsoft.

# Addon Maker for MCPE

A desktop GUI for creating Minecraft Bedrock Edition add-on projects.

## Phase 1

- Dark desktop dashboard.
- Create projects with Behavior Pack (BP) and Resource Pack (RP) folders.
- Generate starter manifest.json files with unique UUIDs.
- Windows x64 build workflow using GitHub Actions.

The content-editor cards are UI entry points for later phases. The 3D viewport, OBJ/FBX import, animation tools, fitting tools and .mcaddon packaging are not implemented yet.

## Windows 7 compatibility target

The project is pinned to Python 3.8.10 and PySide2 5.15.2.1 as a legacy Windows target. The produced executable still needs testing on a clean Windows 7 SP1 x64 machine. If Windows reports a missing runtime DLL, the Microsoft Visual C++ 2015-2019 x64 runtime may be required.

## Run from source

    py -3.8 -m pip install -r requirements.txt
    py -3.8 src\main.py

## Build locally

    py -3.8 -m PyInstaller --noconfirm --clean --windowed --name AddonMaker --collect-all PySide2 src\main.py

The executable is created under dist\AddonMaker\AddonMaker.exe.

## Build with GitHub Actions

Open the repository Actions tab, select Build Addon Maker for MCPE, and run the workflow on branch phase1-dashboard. Download the AddonMaker-Windows-x64 artifact from the completed run.

## Roadmap

1. Dashboard and project generator.
2. Item, armor, block and entity editors.
3. Bedrock geometry preview and model import.
4. Animation and fitting tools.
5. Pack validation and .mcpack / .mcaddon export.

This is an unofficial community tool and is not affiliated with Mojang or Microsoft.

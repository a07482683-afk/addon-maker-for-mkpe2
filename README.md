# Addon Maker for MCPE

A desktop GUI for creating Minecraft Bedrock Edition add-on projects.

## Current features

- Dark desktop dashboard and project generator.
- Creates linked Behavior Pack (BP) and Resource Pack (RP) folders with unique starter manifests.
- Texture Studio: 16/32/64/128/256 pixel canvas, pencil, eraser, flood fill, eyedropper, alpha color picker, pixel grid, undo, PNG import/export.
- Layered texture projects: add, delete, duplicate, rename, reorder, hide/show and adjust opacity for layers. Save and reopen editable .tstudio projects; export a flattened PNG.
- Visual Event Sheet: choose supported Bedrock event triggers and actions using a Construct-style WHEN → DO workflow.
- Event Sheet export to JSON and starter JavaScript Script API generation.
- Direct code tabs for Bedrock JSON, JavaScript Script API, Molang and mcfunction.
- Windows x64 build workflow via GitHub Actions.

The event-to-JavaScript generator creates starter code for the selected event/action rows. Check event availability and API names against the Script API version enabled by the target Bedrock world; this is not a full compiler for every possible Bedrock event.

## Planned next phases

- Live Bedrock texture atlas/project integration.
- Item, armor, block and entity editors.
- Bedrock geometry preview and OBJ/FBX model import.
- Animation timeline and fitting tools.
- Pack validation and .mcpack / .mcaddon export.
- Larger event and action library, validation and project-wide code generation.

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

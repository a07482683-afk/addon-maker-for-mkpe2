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
- Item editor: generates a starter Bedrock item JSON file with identifier, display name, creative category, icon key, stack size and foil setting.
- Block editor: generates a starter Bedrock block JSON file with identifier, display name, creative category, mining time, friction, light emission and map color.\n- Armor editor: creates wearable item definitions with slot, protection and durability settings.\n- Resource Pack Texture Registry: copies PNG icons into RP/textures/items and merges keys into textures/item_texture.json without discarding existing atlas entries.
- 3D model workspace: imports OBJ and ASCII FBX, displays a rotatable/zoomable mesh preview, maps OBJ object/group sections to Bedrock bones, exports fitted cuboid parts, and creates a simple looping rotation animation JSON.
- .mcaddon export: validates BP/RP manifests and packages both packs into one archive.
- Windows x64 build workflow via GitHub Actions.

The item, armor and block editors save starter JSON into the selected Behavior Pack. The texture registry copies PNG files into the selected Resource Pack and updates the item texture atlas while preserving existing entries. Definitions are starter templates and should be checked against the target Bedrock version. The 3D preview imports OBJ and ASCII FBX; binary FBX is not supported. Geometry export creates one fitted cuboid per OBJ object/group (or one root cuboid for FBX). It does not preserve the original triangle surface or transfer OBJ UV coordinates to cube faces yet. Animation export currently creates a simple looping root-bone rotation with start/end keyframes; it is a starter animation, not a full timeline editor. The .mcaddon exporter packages existing BP and RP folders; it does not guarantee runtime validity.\n\nThe event-to-JavaScript generator creates starter code for the selected event/action rows. Check event availability and API names against the Script API version enabled by the target Bedrock world; this is not a full compiler for every possible Bedrock event.

## Planned next phases

- Live Bedrock texture atlas/project integration.
- Armor and entity editors, plus expanded validation and resource-pack texture registration.
- UV-aware cube face mapping, finer mesh fitting, bone hierarchy editing and a multi-keyframe animation timeline.
- Deeper Bedrock schema and runtime validation.
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

Open the repository Actions tab, select Build Addon Maker for MCPE, choose branch phase6-geometry-uv-bones, and run the workflow. Download the AddonMaker-Windows-x64 artifact from the completed run.

This is an unofficial community tool and is not affiliated with Mojang or Microsoft.

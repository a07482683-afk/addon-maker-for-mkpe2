# Addon Maker for MCPE

Программа для создания аддонов Minecraft Bedrock. Главная страница ведёт пользователя по шагам: создать проект → выбрать редактор → собрать файл .mcaddon.

## Что добавлено в Phase 8

- Русский интерфейс главной страницы, Texture Studio, конструктора событий и 3D-редактора.
- Проекты запоминают последний открытый путь и настройки; последний проект автоматически открывается при следующем запуске.
- Рисование иконки предмета прямо в редакторе на сетке 16×16: ЛКМ рисует, ПКМ стирает; PNG автоматически сохраняется в RP и регистрируется в item_texture.json.
- Конструктор событий с большим списком WHEN-триггеров и DO-действий, цветными карточками, добавлением/удалением правил, сохранением JSON и генерацией JS.
- Учебные примеры предмета, блока, структуры биома и событий в папке Examples нового проекта.
- 3D-редактор: импорт OBJ/ASCII FBX, вращение/масштаб, ракурс Minecraft и сохранение снимка предпросмотра.
- Усиленная проверка экспорта: manifests, UUID, JSON-файлы, целостность обоих mcpack и итогового mcaddon.

## Важные ограничения

- FBX поддерживается только в ASCII-виде; бинарный FBX нужно предварительно экспортировать в OBJ или ASCII FBX.
- Геометрия Minecraft пока является приближённым экспортом из частей-мешей в кубы, не точным переносом произвольной сетки и UV.
- Предпросмотр 3D — визуализация формы внутри редактора, а не рендер движком Minecraft. Для проверки фактического вида импортируйте аддон в игру.
- События Script API и биомы зависят от версии Minecraft Bedrock; примеры помечены как учебные и требуют проверки. Не все перечисленные триггеры гарантированно существуют во всех версиях API.
- Внутренняя проверка mcaddon подтверждает структуру архивов и JSON, но не может запустить Minecraft и доказать, что игра примет каждый компонент.
- Целевая связка для старых ПК: Python 3.8.10 x64, PySide2 5.15.2.1, PyInstaller 5.13.2. Реальная совместимость EXE с чистой Windows 7 SP1 x64 требует отдельного теста.

## Запуск из исходников

Установите зависимости из requirements.txt, затем запустите python src/main.py.

## Phase 15 — MCPE 1.7.0 / ModPE Studio

- Отдельное окно **MCPE 1.7.0 — ModPE Studio** в меню «Создать».
- Редактор JavaScript с шаблоном ModPE и вставкой примеров для предметов, блоков, рецептов и взаимодействия с существующими сущностями.
- Импорт PNG в отдельную папку `LegacyTextures/blocks`, `LegacyTextures/items` или `LegacyTextures/entities`.
- Старые скрипты сохраняются в `ModPE/*.js`; они предназначены для совместимого BlockLauncher/ModPE, а не для импорта как современный `.mcaddon`.
- Это генератор и редактор скриптов, а не эмулятор Minecraft: совместимость каждого вызова API нужно проверить в конкретной сборке BlockLauncher.
- MCPE 1.7.0 не получает полноценный конструктор пользовательских биомов; новые сущности ограничены возможностями ModPE и существующими игровыми типами.


## MCPE 1.7.0 export

When the project target version is **1.7.0**, Export now uses a legacy-aware `.mcaddon` container:
- includes the Behavior Pack and Resource Pack as `.mcpack` files;
- includes ModPE `.js` files under `LegacyModPE/scripts/`;
- includes imported legacy PNGs under `LegacyModPE/textures/`;
- includes a README explaining how to use the legacy files.

Important compatibility note: Minecraft PE 1.7.0 does not execute ModPE JavaScript from a `.mcaddon`. The scripts are carried inside the archive for convenient transfer; running them still requires a compatible BlockLauncher. The export is a container/package, not a conversion of ModPE code into the modern Bedrock Script API.


## Phase 17 — ModPE → Bedrock Script API

- Added **Конвертер ModPE → Script API** to the «Создать» menu.
- Reads JavaScript files from `ModPE/*.js`, generates `BP/scripts/main.js`, adds a Script module to `BP/manifest.json`, and declares the selected `@minecraft/server` dependency.
- Converts a limited set of common patterns, including `clientMessage`, basic player coordinate references, and legacy event callback shapes.
- Writes `ModPE/conversion-report.json` with per-file warnings.
- Calls that require declarative content (custom items, blocks, recipes) are not falsely presented as runtime conversions: the report instructs the user to migrate them into Behavior Pack / Resource Pack JSON.

**Important:** this is a best-effort source migration tool, not a universal JavaScript compiler. ModPE and Bedrock Script API are different environments. Every generated script must be reviewed and tested against the exact Minecraft Bedrock version; unsupported APIs and gameplay behavior need manual migration. The old MCPE 1.7.0 client cannot run the modern Script API.

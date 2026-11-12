import json
from pathlib import Path
def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
def create_learning_examples(project):
    project = Path(project)
    examples = project / "Examples"
    _write(examples / "items" / "glow_gem.json", {
      "format_version":"1.20.50","minecraft:item":{
       "description":{"identifier":"demo:glow_gem","menu_category":{"category":"items"}},
       "components":{"minecraft:icon":"glow_gem","minecraft:max_stack_size":16,"minecraft:glint":True,
                     "minecraft:display_name":{"value":"Светящийся самоцвет"}}},
      "_lesson":"Измените ID, имя, размер стопки и иконку. Добавьте glow_gem в item_texture.json."})
    _write(examples / "blocks" / "moon_stone.json", {
      "format_version":"1.20.50","minecraft:block":{
       "description":{"identifier":"demo:moon_stone","menu_category":{"category":"construction"}},
       "components":{"minecraft:destroy_time":2.0,"minecraft:explosion_resistance":6.0,
                     "minecraft:friction":0.6,"minecraft:map_color":"#7C78A8","minecraft:light_emission":4}},
      "_lesson":"Попробуйте менять прочность, сопротивление взрыву, свет и цвет. Сверяйте компоненты с версией игры."})
    _write(examples / "biomes" / "crystal_valley_learning.json", {
      "format_version":"1.21.0","minecraft:biome":{
       "description":{"identifier":"demo:crystal_valley"},
       "components":{"minecraft:climate":{"downfall":0.1,"snow_accumulation":[0.0,0.0],"temperature":0.8},
        "minecraft:surface_parameters":{"sea_floor_depth":7,"sea_floor_material":"minecraft:gravel",
         "foundation_material":"minecraft:stone","mid_material":"minecraft:stone","top_material":"minecraft:grass"}}},
      "_lesson":"Учебная структура биома. Генерация и поддержка зависят от версии Bedrock и экспериментов; пример не гарантирует появление биома в мире."})
    _write(examples / "events" / "starter_events.json", {
      "format_version":1,"events":[
       {"trigger":"Игрок появляется в мире","action":"Отправить сообщение в чат","value":"Добро пожаловать!"},
       {"trigger":"Игрок использует предмет","action":"Выполнить команду","value":"playsound random.orb @s"}],
      "_lesson":"Добавляйте правила WHEN → DO и сверяйте события с версией Script API."})
    (examples / "README.txt").write_text("УЧЕБНЫЕ ПРИМЕРЫ\n\nИзучите JSON и меняйте значения. Не копируйте шаблоны без проверки версии Bedrock. Биомы требуют отдельной проверки поддержки и экспериментальных настроек.\n", encoding="utf-8")
    return examples

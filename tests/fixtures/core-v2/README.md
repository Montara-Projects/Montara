# Fixture de contrato existente para #415

`stage-recipe-v1.json` es una receta sintética de seis segundos, dos fuentes,
tres cortes, velocidad por shot y luz independiente. No contiene medios,
rutas personales, credenciales ni un schema V2 propuesto. El Engine es el pin
Git de la baseline examinada, no una afirmación sobre una app instalada.

Solo se ha validado la normalización con `companion/video_recipe.py`:

```sh
python3 - <<'PY'
import json
from pathlib import Path
from companion.video_recipe import validate
p = Path('tests/fixtures/core-v2/stage-recipe-v1.json')
recipe = json.loads(p.read_text())
assert validate(recipe) == recipe
assert validate(validate(recipe)) == recipe
assert sum(s['duration_sec'] for s in recipe['segments']) == 6
assert [s['source'] for s in recipe['segments']] == [0, 1, 0]
print('PASS: contrato Stage v1, no render ni E2E V2')
PY
```

No ejecutar un render hasta aportar dos fuentes sintéticas autorizadas de al
menos seis segundos y un máster sintético, resolverlas por el mecanismo local
existente y disponer del Engine/runtime fijado. No usar proyectos de usuarios.
La resolución, códecs y calidad se fijarán en el perfil de la prueba de render;
este validador no los recibe como campos libres de receta.

Pendientes explícitos para FER/JM: envolver el plan en identidades de dominio
owner/project/asset/representation, revisión, song/interval y job/task/attempt.
El validador actual no transporta esos campos: añadirlos al JSON y llamar a
`validate` no demuestra que sobrevivan. La autorización corresponde a la capa
de trabajo, no a esta receta data-only.

Multisong, offsets, 360, captions y modos Push/Show requieren fixtures adicionales
con su contrato revisado. Esta fixture no certifica esos recorridos.

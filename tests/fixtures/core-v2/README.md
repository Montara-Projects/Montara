# Fixture de contrato existente para #415

`stage-recipe-v1.json` es una receta sintética de seis segundos, dos fuentes,
tres cortes, velocidad por shot y luz independiente. No contiene medios,
rutas personales, credenciales ni un schema V2 propuesto. El Engine es el pin
Git de la baseline examinada, no una afirmación sobre una app instalada.

La normalización con `companion/video_recipe.py` puede comprobarse sin medios:

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

## Banco audiovisual generado y verificador

El siguiente comando crea una carpeta **nueva** con dos cámaras H.264/AAC de
seis segundos y un máster PCM sintético. Si el destino existe, falla sin
sobrescribirlo. No se suben medios ni se consulta ningún servidor.

```sh
python3 tools/core_v2_media_fixture.py generate /tmp/core-v2-fixture-NUEVO
```

- Cámara A: rojo y tono 223 Hz; cambia a verde en el segundo 3.
- Cámara B: azul y tono 443 Hz; cambia a amarillo en el segundo 3.
- Máster: tono 997 Hz, distinto de ambas cámaras.
- `fixture-manifest.json`: tamaños, SHA-256 y versión FFmpeg; se escribe al
  terminar. Su ausencia indica generación incompleta.
- `recipe.json`: copia exacta de la receta revisada, sin rutas de medios.

El montaje esperado alterna A→B→A. La segunda toma reproduce desde el segundo
2 a velocidad 1,5: en el segundo 2,8 del montaje ya debe verse amarillo. Así
el verificador puede detectar tanto cámara equivocada como velocidad/tiempo
de fuente incorrectos. Los puntos de color evitan los fundidos inicial/final
que ya aplica el exportador nativo. La comparación no depende de una fuente
tipográfica, OCR, servicio de IA o hashes idénticos entre encoders.

Para verificar un MP4 producido por el **renderer real**, sin volver a renderizar:

```sh
python3 tools/core_v2_media_fixture.py verify /tmp/core-v2-fixture-NUEVO /ruta/al/resultado.mp4
```

Exige integridad de los cuatro inputs, H.264 1920×1080 + AAC, seis segundos
(±0,15 s), decodificación completa, cinco muestras de cámara/tiempo y el máster
997 Hz dominante en tres ventanas. No certifica detalle nativo 1080p (inputs
640×360), ASR, sync acústica real, calidad perceptual, 360, OAuth o aislamiento.
La tolerancia temporal es provisional para esta fixture, no SLA del producto.
El manifiesto es evidencia local de QA, no una firma ni una raíz de confianza.

Para ejecutar el exportador existente en scratch, con el Engine fijado y sin
usar el Companion instalado:

```sh
git submodule update --init --depth 1 engine
python3 -m venv /tmp/core-v2-qa-NUEVO
/tmp/core-v2-qa-NUEVO/bin/python -m pip install -r tests/requirements-core-fixture.txt
MONTARA_CORE_FIXTURE_RENDER=1 /tmp/core-v2-qa-NUEVO/bin/python -m pytest tests/test_core_v2_media_fixture.py -q
```

El gate usa `VideoJobs` y `local_video.py`, comprueba que el render leyó los
originales sintéticos, que sus hashes no cambian y que el resultado sobrevive
a recrear el gestor de jobs. Los casos negativos rechazan inputs alterados,
enlaces simbólicos, una cámara sin montar y el audio de cámara en lugar del
máster. Sin la variable de opt-in, las tres pruebas que requieren Engine se
marcan explícitamente pendientes; eso no constituye PASS de render.

El workflow `CORE V2 synthetic media gate` repite el ensayo en Linux y conserva
solo informes sintéticos durante siete días. No instala paquetes en una VM,
no utiliza secretos y no publica instaladores. Su resultado debe comprobarse
en Actions antes de declarar Linux PASS. Es prueba de componentes V1
reutilizables para V2, no el slice V2 completo.

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

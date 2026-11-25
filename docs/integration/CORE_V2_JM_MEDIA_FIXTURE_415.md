# #415 — banco audiovisual JM y gate de reutilización

25-11-2026. Segundo lote, dependiente de PR #416. Sin implementación del Core,
sin despliegue ni cambios de servicios, proyectos reales o Companions instalados.

## Entrega

- `tools/core_v2_media_fixture.py`: genera medios sintéticos mínimos y verifica
  outputs; **no es otro renderer**. FFmpeg/ffprobe y biblioteca estándar.
- `tests/test_core_v2_media_fixture.py`: usa el `VideoJobs`/`local_video.py`
  existentes y el helper de layout aislado de `tests/test_local_video.py`.
- `tests/requirements-core-fixture.txt`: entorno acotado de QA; no sustituye
  el lock de distribución ni requisitos de producción.
- `.github/workflows/core-v2-media-fixture.yml`: mismo gate en Linux para PR
  relevantes, solo lectura de repo, sin secretos, sin despliegue ni servicios.
- Guía y comandos en `tests/fixtures/core-v2/README.md`.

## Resultado Mac comprobado

Engine `9af275b18535005e36bd289a68ceb4a1d2f6c506` checkout exacto, sin editar.
Mixer `f15ff91c1b80fc5f157099dcd9451d958d553ae6` no ejecutado/modificado.
Python 3.12, FFmpeg 8.1.2, NumPy 1.26.4, OpenCV headless 4.11.0.86;
resto de dependencias QA fijadas en el fichero anterior. Entorno nuevo aislado;
ninguna instalación global ni actualización de Companion.

```sh
MONTARA_CORE_FIXTURE_RENDER=1 python -m pytest tests/test_core_v2_media_fixture.py -q
python -m pytest tests/test_local_video.py -k 'recipe or neutral_interval' -q
```

- **9/9 PASS**, incluyendo un render real, recuperación de output al recrear
  VideoJobs y casos negativos; 29,52 s en la ejecución verificada.
- **22/22 PASS** de receta/intervalos existentes; 3 pruebas de render de ese
  fichero no seleccionadas, distintas del nuevo render que sí se ejecutó.
- MP4: **6,000 s, 1920×1080, H.264 + AAC, 224.764 bytes**, decode completo PASS.
- SHA-256 MP4 Mac:
  `c539838673f2f1d615ed66ea9b74b7ad03c705516efcc24cb9d258e8729533d1`.
- Cinco muestras rojo→azul→amarillo→amarillo→verde; incluye cruce del marcador
  temporal por reproducción a velocidad 1,5 de la segunda toma.
- Tono de máster 997 Hz dominante en ventanas de segundos 1/3/5; se rechaza
  remux con audio 223 Hz de cámara. Los originales sintéticos conservan hashes.
- Manifest de render confirma las dos fuentes locales sintéticas, sin proxies.
  No prueba la autorización de un portal: no se inició ningún servidor HTTP.
- Inputs y resultado conservados privadamente en el Mac, menos de 1 MiB en
  conjunto; no se añaden binarios a Git ni se copian medios personales.

Primera ejecución: el oracle tomó el segundo 0,5 dentro del fundido de entrada
nativo y rechazó su rojo oscurecido. Se verificaron muestras de frames y el
fundido existente; se eligieron checkpoints fuera de los bookends manteniendo
el umbral de color. No hubo cambios de Engine para hacer pasar la prueba.

## Linux y CI general

El resultado Linux del workflow nuevo debe comprobarse en la PR antes de
marcarlo PASS. No equivale a E2E de producto ni a V2 integrado.

En PR #416, CI general consultada: Stage/Push/Mix/Engine/private-container PASS;
Session FAIL en `tests/e2e_session_video.py:61`, esperando
`montaraCompanion.info !== null` durante diez segundos. Git main `7113fd2`
también registra CI E2E fallida; no se atribuye por ello una causa idéntica sin
comparar sus logs. Este lote no modifica frontend/detección para ocultarlo ni
declara toda la suite verde. El fallo de Session se coordina separadamente.

## Límites y siguiente integración

Es evidencia reutilizable del exportador actual, no un Core V2 operativo,
release reproducible certificado ni instalación firmada. Las fuentes son
640×360: verificar output 1080p no acredita detalle original 1080p.
No cubre 360, sync musical real, captions, Google Login, aislamiento de owners,
red, autorización de dispositivo, instalación Mac/Windows o portabilidad cloud.
Los hashes de outputs pueden diferir entre FFmpeg/OS; se verifica contenido,
tiempos y audio, no igualdad binaria entre encoders distintos.

FER puede usar los mismos inputs/oracle para su slice Linux una vez acordado
el contrato v0. No se propone otro catálogo, scheduler o API de producto. Un
manifest local de QA no es un contrato V2 ni firma de procedencia de release.
Publicar el manifest de ejecución sin rutas privadas y registrar qué Engine
produjo realmente el output. No subir originales reales ni abrir puertos.

Rollback: revertir este lote de herramientas/tests/workflow. No hay migraciones,
servicios instalados ni datos de aplicación que restaurar. No integrar ni
desplegar automáticamente por una prueba focalizada.

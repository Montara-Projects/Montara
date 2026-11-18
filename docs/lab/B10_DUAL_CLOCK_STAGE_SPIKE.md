# B10 · Separación entre línea temporal, referencia acústica y escucha
Estado: **spike de contrato aislado**; sin conexión al editor, backend ni despliegue. Derivado de main 9bd5a8d + B9. 18/11/2026.

## Hallazgos comprobados en el código actual
1. En `mixer_adapter/session.py::execute(action='detect')`, el caso `video_excerpt` **ejecuta `session_listen(work)` de toda la jam** antes de poner estado `review`. No ejecuta detección completa de canciones. La guía se crea desde las pistas y offsets, y su onda queda en `waveform.json`.
2. `full_session.py::video_sync_source` devuelve `session_listen(work)` como ruta `master`, pero no ofrece metadatos de tiempo global separados. El navegador en `web/full-session.js::mixSessionForVideo` pide ese máster completo y se lo pasa a `/wizard/draft` y `/wizard/prepare` para que el Engine sincronice las cámaras. El resultado alimenta `SessionVideo.excerptForClips` / `SyncSelection`.
3. El endpoint existente `/montara/session/<id>/listen?start=S&end=E` crea fragmentos de escucha desde todas las pistas, acotados a **0,5–3600 segundos**. Se utiliza como alternativa disponible de escucha, pero **su existencia NO evita por sí sola el trabajo de creación de guía completa durante `detect`**, ni suministra un master apto para `wizard/prepare`.
4. Audio-only Full Session tiene otro camino de detección de canciones y mezcla: **conservarlo exactamente**. La mezcla final por canción usa rangos selectivos del original local; no confundir con guía aproximada.

## Contrato de dos relojes: aportación concreta B10
`web/hybrid-session-clock.js` es **una maqueta pura sin HTTP**: `timeline` declara duración de jam global (14.248 s) separada de la ventana de referencia corta (p.ej. [2235,3297]); `rangeRequest` prepara solo la URL de escucha acotada existente, validando identidad y límites; `prepareExcerpt` cruza B9 offsets globales verificados por Engine con el intervalo musical elegido y prueba que la lectura sigue anclada al reloj global. Todo devuelve `stage_ready:false`: un Ogg de escucha / guía corta **no es un máster Stage**, y `wizard/prepare` sigue recomputando Sync a partir de un archivo realmente existente.

La separación conceptual es:
- **Reloj global**: `session.id`, duración full, instrumentos, identidad de sesión, rangos de canciones y cámaras.
- **Referencia Sync (acústica)**: fuente/copia corta, `window_global_start`, duración, versión de receta y pruebas de consenso; el Engine realiza la verificación y B9 aplica proyección global.
- **Escucha**: audio acotado y escuchable con ruta autorizada existente; no intercambiable con máster de exportación.
- **Máster de edición/export**: un producto real de mezcla por rango y un contrato autorizado para `wizard/prepare`. Hoy requiere el máster completo; ninguna ruta B10 afirma lo contrario.

## Integración progresiva pactada (propuesta, no autorización de despliegue)
- **Gate 0 — #267 / A/A Mac CHEMA**: medir primer gesto→canciones editables en jam real, con Companion habitual intacto; resultados anonimizados, misma red y caché. Ambos laboratorios pueden implementar y fusionar en main en coordinación; **Chema ejecuta E2E largo en su Mac con sus medios**.
- **Gate 1 — Contrato, sin cambios funcionales**: B9+B10 tests, revisión de límites y propuesta de interfaz backend de sincronización global desacoplada; no crear otra detección ni sincronización.
- **Gate 2 — Backend por ventana, opt-in y aislado**: mecanismo interno de selección/guía corta con identidad de sesión y pistas; autorización/Owner/CSRF, sin acceso arbitrario a rutas, sin subir originales y con límites de recursos, receta versionada. Mantener `session_listen` existente como fallback.
- **Gate 3 — Stage por etapas**: conectar Sync verificado con reloj global, admitir referencia corta para cálculo sin confundirlo con guía de escucha; luego revisar selección de canción, waveform, `wizard/prepare`, `SyncSelection`, Cut/Edit/Export; no dar ready si una cámara duda.
- **Gate 4 — QA y lanzamiento**: tests de seguridad, cortos, 360, múltiples cámaras, discontinuos, cambios de offset, caché fría/caliente, negativos; E2E humano real Mac de Chema con 13 pistas y recorrido completo hasta MP4; A/A→A/B de extremo a extremo para demostrar mejora, rollback y decisión conjunta.

## Requisitos de aceptación y límites
- Sin `engine/` ni `mixer/` editados o repinados como efecto secundario.
- La decisión de `main` es **compartida según colaboración**: coordinar en #216, no atribuir el merge en exclusiva a JM. Chema dispone de los originales y ejecuta las pruebas E2E largas.
- No declarar ahorro ≥30% con benchmarks de fases distintas; comparar en mismo Mac/companion, jam y red.
- Un fallo del prelocalizador de huellas no significa cámara inválida: fallback con Engine completo siempre que se pueda. No aceptar un candidato que no supere confianza + estabilidad.
- `stage_ready:false` es deliberado. El siguiente cambio funcional exige resolver la frontera real de `wizard/prepare`, no ocultarla mediante una propiedad inventada.

Pruebas: `node --test tests/hybrid-session-clock.test.cjs tests/hybrid-stage-contract.test.cjs tests/test_sync_selection.cjs tests/test_session_video.cjs`. Esto no acredita que la UI actual use B10.
# B11 — Backend híbrido Stage: contrato y prueba aislada (18/11/2026)

**Estado:** prototipo de laboratorio y puerta de revisión técnica, **NO integración funcional de Stage**, no despliegue.
**Base:** B10 `3725b09`, derivada de `main@9bd5a8d`.
**Rama:** `fernando/b11-hybrid-backend-lab`.
**Dependencia:** `#265` B0–B10, `#273` B9 draft, `#267` medición Full Session.
**Código aportado:** `hybrid_video_b11.py` y `tests/test_hybrid_video_b11.py`; no se cambian módulos productivos, rutas, `engine/`, `mixer/`, servicios ni la arquitectura Cloudflare.

## Resultado principal

B11 demuestra en un checkout aislado que **un backend puede construir una referencia real corta utilizando el mezclador acotado existente** (Ogg de intervalo) sin crear `listen-all.webm`, conservar la duración global y reproyectar evidencia de sincronización suministrada por un ejecutor Engine confiable. **No demuestra que el Stage actual utilice ese camino**, porque su detección de vídeo genera hoy la guía completa y el Wizard aún requiere `master` de sesión.

### B11.1 — Sesión, fuentes, dueño y receta

- `load_session(data_root, session_id, principal, authorize)` resuelve el trabajo desde `data_root/Sessions/{id}`, **nunca** desde una ruta de cliente. Validación estricta de ID, manifiesto, modo vídeo, 1–128 pistas, offsets, duración y origen dentro de raíz autorizada. Audio-only se rechaza expresamente para esta API.
- La autorización `authorize(principal, session_id)` es obligatoria y fail-closed. `make_owner_csrf_guard()` puede reutilizar el **SessionStore real** con verificación de sesión, CSRF, caducidad/revocación y una asignación `session_id→owner_id` que debe suministrar el registro Owner de confianza.
- El enlace efectivo con ese registro y la validación HTTP de Origin **no existen aún en producto**. No hay endpoint público nuevo. **No se debe montar** el módulo simplemente pasando un `lambda: True`.
- La identidad `recipe_id` deriva de metadatos de fuente y receta; detecta alteraciones normales de tamaño/mtime/offset. **No equivale a un SHA integral del medio original**: una cache distribuida comercial requerirá huella/recibo de fuente confiable.

### B11.2 — Guía acústica corta real

- `prepare_short_guide()` reutiliza `mixer_adapter.session.listen_range` sin modificarlo, con intervalo de **0,5–3600s** y límites normalizados a centésimas (como los nombres de caché del módulo existente).
- Se genera **audio real Ogg/Opus** desde WAV sintéticos pequeños mediante FFmpeg y se comprueba con `ffprobe` (duración, existencia, bytes). Las fuentes no se modifican y no se construye `listen-all.webm`.
- Caché propia `Sessions/{id}/b11-cache/{recipe_id}`, lock, instantánea de pistas, invalidación al cambiar origen/receta y rechazo de symlinks peligrosos. No se altera `listen/` ni la caché heredada del producto.
- **Límite:** `mixer_adapter/session.py::execute(detect, video_excerpt)` no llama todavía a B11; sigue creando la guía completa antes de review. Un futuro opt-in tendrá que desacoplar también waveform/listening y comprobar cancelación/recursos.

### B11.3 — Engine nativo, desplazamientos y fallback

- `run_trusted_engine_window` es el **punto de conexión**, no un Engine duplicado. Recibe referencia local interna y los IDs opacos de cámaras; el ejecutor autorizado es quien debe resolver sus medios y llamar al Engine pinneado.
- `project_engine_evidence` sólo acepta resultados de Engine previamente verificados: confianza, estabilidad, `consensus_count`, cobertura y todas las cámaras. Conserva `offset_ranges` por separado, incluidos huecos y offsets negativos con solapamiento válido. Calcula `offset_global = inicio_ventana + offset_local`.
- Fallo de cualquier cámara → **rechazo de lote**, sin publicar resultado parcial. `fail_closed_fallback` expresa que se necesita el Engine tradicional, pero **no lo ejecuta automáticamente**. El fallback real de Wizard/Stage sigue pendiente.
- Las pruebas B11 utilizan un ejecutor simulado para el contrato; **B5/B8 son la evidencia histórica de funciones Engine reales**, no se ha repetido su ensayo largo en B11.

### B11.4 — Compatibilidad Stage y música

- `stage_contract_plan` conserva ventana de canción **en reloj global** y la relación de cámaras, pero responde siempre `stage_ready: false`.
- No se sustituye un máster de cuatro horas por una guía breve, no se declara ready sin `/wizard/prepare` adaptado, ni se modifica la detección/revisión audio-only.
- Pendientes genuinos: Owner API de intervalo, `wizard/draft` y `wizard/prepare` con offsets Engine globales de confianza, `SyncSelection` con huecos, waveform/escucha sin bloquear por guía completa y `Cut/Edit/Export` desde rangos originales.
- La base de pruebas JS B9/B10, `SessionVideo` y `SyncSelection` se vuelve a ejecutar como regresión; **no prueba la UI de B11**.

### B11.5 — QA y verificación

Cobertura de laboratorio: Owner autorizado y denegado, sesión real `SessionStore` con CSRF rotado/revocado, audio-only no afectado, rutas extranjeras bloqueadas, ventanas mal formadas, Ogg/Opus real por intervalo, ausencia de guía completa, caché versionada, mutación de fuente mientras se genera, symlink de caché, dos cámaras, identificador 360, intervalos discontinuos, offsets negativos, confianza deficiente y silencio, plan Stage no ready.

**Comandos reproducibles** (venv Python con pytest/Flask/NumPy/SoundFile y FFmpeg/ffprobe):
```bash
python -m pytest tests/test_hybrid_video_b11.py -q
node --test tests/hybrid-stage-contract.test.cjs tests/hybrid-session-clock.test.cjs tests/test_sync_selection.cjs tests/test_session_video.cjs
python -m py_compile hybrid_video_b11.py
git diff --check
```

**No se han realizado:** E2E navegador, las 13 pistas originales en Mac, Sync nativo en el nuevo camino B11, despliegue HTTPS/Cloudflare, lectura de proyectos de otros usuarios, render/export MP4 B11 ni benchmark WAN. No declarar aceleración porcentual.

## Handoff A–E para Chema / IA de Chema

**A. Novedades.** Contrato y prueba real de guía acústica corta independiente, identidad versionada, puerta Owner/CSRF, proyección temporal estricta y plan Stage fail-closed.

**B. Duplicidades evitadas.** Reutilización de `listen_range`, `SessionStore`, Engine nativo (futuro adaptador) y contratos B9/B10; sin nueva detección de canciones, motor, Mixer, infraestructura ni acceso a originales.

**C. Reutilización posterior.** Conectar B11 a `video_excerpt` opt-in y al gateway Owner mediante registro dueño/sesión; exponer a Stage evidencia Engine verificada en tiempo global, no rutas absolutas. Mantener toda la ruta tradicional como fallback.

**D. Riesgos.** Contrato de `master` en Wizard; waveform/escucha bloqueantes; autorización propietario real todavía no conectada; caducidad/integridad fuerte de caché; clips con huecos, 360, VFR/deriva, recursos, concurrencia de trabajos y rollback. `stage_ready:false` obligatorio.

**E. Recomendación.** Revisión técnica compartida en #216 antes de tocar piezas comunes. Mantener `#267` como primer benchmark A/A Mac; solicitar a JM un ACK técnico sobre el contrato `master/sync`, Owner y selección de canciones. Continuar implementación opt-in **solo** después de acordar la frontera pública. Para QA final Chema debe ejecutar con sus fuentes de 13 pistas y Mac.

## Matriz de aceptación

| Gate | Estado de este laboratorio | Qué falta para producto |
| --- | --- | --- |
| B11.1 identidad/autorización | Modelo, callback y tests PASS | Enlace real a Owner sesión-proyecto, HTTPS/Origin |
| B11.2 referencia corta | Ogg real y aislamiento PASS | Invocación opt-in desde `detect(video_excerpt)`, waveform independiente |
| B11.3 Sync | Proyección/verificación de contrato PASS | Ejecutar Engine real en este camino + fallback tradicional |
| B11.4 Stage | Plan seguro `stage_ready:false`, regresión JS | Wizard, editor, selección, escucha y export reales |
| B11.5 seguridad/QA | Suite aislada PASS | E2E largo Mac JM, matriz de fuentes/negativos, métricas A/A→A/B |

**Convergencia arquitectónica:** `main` compartido y Cloudflare Workers/Tunnel como arquitectura principal acordada por Fernando y Chema. Work/Multisong es laboratorio aislado; sus mejoras útiles pueden integrarse mediante revisión, **sin establecer por omisión otro canal oficial ni un segundo contrato Companion**. No modificar infraestructura aquí.

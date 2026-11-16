# O1 · ÓRBITA — Optimización híbrida real (inicio 2026-11-16)

**Base:** `main@e92422643770e27f95d482ab175846c447a0aa27`  
**Rama:** `fernando/o1-orbita-20261116`  
**Estado:** fase de medición; no cambia runtime, hosting, Companion instalado ni motores.

## Por qué O1 y no I6/I7

I6a/b/c cerraron la integración del cierre seguro/guardas de apagado en código; I7a integró aceptación automatizada de dos propietarios, pero no certifica Google real simultáneo ni Windows+Mac. El E2E humano del 16/11 valida una persona con Google/H4/Windows/Companion/Stage/MP4 descargado, no reproducción final consignada ni varias cuentas. Es nuestra base funcional para medir, **no** benchmark de rendimiento ni QA de Mac.

La rama `fernando/i6-performance-baseline-20261116` está exactamente dos commits detrás de `main`: la diferencia es exclusivamente `docs/COLLABORATION.md`, `docs/integration/I5B_STAGE_VIDEO_WINDOWS_E2E_CHEMA_HANDOFF_2026-11-16.md` y `docs/lab/STATUS-FER.md`. No altera código de ejecución.

## Fuentes existentes: recuperar selectivamente, NO mergear ramas antiguas

- `fernando/integracion`, PR #177: `tests/urano_hybrid_node_meter.py`, `tests/urano_hybrid_merge_reports.py`, `tests/urano_browser_transfer.py` y preflight remoto; **no están en main**. El reducer antiguo exige >=2 Companion: adaptar/crear validación estricta de una persona antes de usarlo como baseline O1; no falsificar topología. El preflight antiguo consulta una ruta del editor clásico: revisar rutas OAuth/H4, no copiarlo directamente.
- PR #130–132: mediciones en runner compartido, no PC real ↔ VM. Reutilizar controles de privacidad y medición pasiva, nunca presentar los datos de CI como benchmark WAN.
- PR #141 (fusionada): telemetría de preparación de proxy y subida a revisar en el flujo actual.
- `docs/integration/PROCESOS_Y_ESTUDIOS_DE_OPTIMIZACION_HIBRIDA_2026-11-12.md` en commit `5182974`: proxies según tarea, originales inmutables locales, reglas locales/remotas con coste completo. Sus afirmaciones sobre H4 *anterior al E2E* son históricas.
- `docs/lab/INVENTORY-FER.md`: SATURNO GOP/transferencia, JÚPITER 360, FOCUS proxy-edit/original-export, cachés, límites y casos descartados. Historial científico, no autorización para integrar.
- PR #151/#159/#213 de JM: caché 360, miniaturas y máster audio; evitar cambios duplicados/Engine SHA inconsistente.
- Issue #216: coordinación entre IA Fernando/Chema antes de cambios sobre contratos comunes.

## Primera medición: O1.1 (1 usuario, 2 hosts reales)

**Topología obligatoria:** Windows 10 + Chrome + `Montara.Companion.Service.exe` local, Google OAuth/H4 mediante HTTPS, VM GCP remota. Etiquetar cada host, PID y versión/commit por separado; no confundir CPU del PC con CPU de servidor.

**Dos recorridos del mismo proyecto/material:**
A. Primer uso (cachés en frío sin purgar datos de usuario).
B. Segundo uso (cachés calientes); nunca borrar originales ni cachés compartidas para forzar frío.

**Fases:** seleccionar carpeta → localizar original → preparar proxy → bytes/tiempo de subida y reintentos → Listening to your videos/sync → construcción/revisión de planos → primer Edit y solicitudes de miniaturas → Save shot → render local → MP4 final/reproducción verificada.

**Métricas por fase y host:** tiempo de pared; CPU-s por árbol de procesos; RSS/pico; disco temporal/cache; bytes enviados por familia de activo y endpoint (metadatos, no cuerpos); frames/codec/resolución; reintentos, errores y tiempos hasta primer editor/resultado. Mantener separados transportes navegador, Companion y servidor: Playwright no observa transferencias Python/FFmpeg ajenas al navegador. No recoger nombres/rutas privados, tokens ni originales.

**Criterios:** mismo proyecto, mismo material, versiones fijadas y resultado A/V verificable; ninguna subida de originales sin consentimiento; aislamiento por propietario; nunca inventar un porcentaje de mejora. Medir en una sesión real y comparar una sola variable cada vez.

## Ruta posterior, según evidencia

O1.2: peticiones Chema — Listening to your videos y pistas largas (preparación, compresión, transferencias).  
O1.3: evitar cómputo y datos innecesarios (proxies condicionales, cachés, extracción local, limitación FFmpeg), cada cambio A/B controlado.  
O1.4: adaptación de Companion con límites de recursos y decisión local/remoto solo para tareas compatibles, respetando privacidad/originales.  
O1.5: comparar E2E y calidad; validar Windows y después macOS con su entorno específico.

**Límites operativos:** no tocar `main`, servicios de Chema, despliegues H4/Cloudflare, apagado automático ni Engine/Mixer; no transferir originales; no generar gastos. Pruebas pesadas y cambios compartidos con coordinación previa en #216. Toda mejora candidata se integra en PR pequeña y revisión cruzada.

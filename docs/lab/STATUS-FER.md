# STATUS — laboratorio Fernando (FER)
Corte: 2026-11-19. Responsable FER. **No equivale a código desplegado.** Coordinación obligatoria: `docs/COLLABORATION.md` y [#216](https://github.com/amehcgracia-byte/Montara/issues/216).
- **Memoria acumulativa:** [HISTORY-FER](HISTORY-FER.md) (octubre–noviembre, sin sobrescribir hitos) y [STATUS original archivado al 05/11](STATUS-FER-ARCHIVE-2026-11-05.md). Este STATUS es una foto breve, no el archivo histórico.

## Base funcional y gobierno
- `main` contrastado: `9bd5a8d`; Engine `92c7bc3`, Mixer `f15ff91`. Verificar de nuevo antes de integrar/desplegar. Integración de piezas compartida/coordinada JM/FER, no fusionar laboratorios completos.
- **Stage Windows E2E humano #255 aprobado** el 17/11: Google→Stage→Companion→Sync→Edit/Save shot→render local→MP4 imagen/sonido correcto. No certifica Mac, 360, multicanción ni todos los formatos.
- **#266 integrado en main**: preflight de cobertura para evitar render sin cámara que coincida. Persisten fallos heredados `e2e(engine)` de #254. No confundir ese rojo global con las CI focalizadas.
- Infraestructura objetivo: **Cloudflare Workers/Tunnel como entrada común prevista** y VM GCP para servicios; JM mantiene beta HTTPS directa **aislada**. Cambiar orígenes, transporte Companion, medios u Owner es ÁMBAR: coordinar ADR y contrato único antes de integración compartida.

## P0–P3 — última evidencia y bloqueos
- **P0 #267** `97bfab4`, OPEN, no merge: telemetría de primera canción editable, PUT y preparación concurrente; segunda tanda tras review inicia nueva cohorte. 9/9 Node métricas + 16/16 batería adicional PASS; 4 workflows focalizados SUCCESS, E2E Linux general FAIL (Engine #254). **JM**: revisar SHA servido/QA Mac y hacer 2 A/A reales con 13 stems ~3h57; después elegir A/B, sin anunciar -30 % antes de medir.
- **Adyacente #270** `cd0a336`, OPEN: log de categoría/errno de `/native/ensure` 503, ACK técnico de Chema; causa del 503 aún no determinada. No tocar ledgers ajenos.
- **P1 #272** `5a2be93`, DRAFT: cierre automático Engine **fail-closed por defecto** (el broker devuelve BusyOwner sin solicitar parada por generación); 18 Python PASS/20 subtests + adaptador Node PASS. **No hay todavía lease multi-pestaña ni barrera atómica RPC**; no merge/activar hasta prueba de dos pestañas, RPC en curso y nueva admisión/cierre, revisadas JM/FER. Cierre manual verificado reservado al operador.
- **P2 #260** `689cb3e`, DRAFT JM: Exports local, abrir carpeta, descarga/reintento; Mac Finder QA aprobado. FER volvió a probar **37/37 Python Linux** con Engine `92c7bc3`, incluidos 2 renders H.264 1080p, sin alterar Companion. **Falta Windows MSIX QA aislado**, Explorer real, reapertura integral, unidad desconectada y SHA; JM mantiene integración.
- **P3** B9 #273 DRAFT sobre main; B10 rama de reloj dual; B11 #274 DRAFT `7766ef5` apilada sobre B10 (NO sobre main). **26/26 pytest B11 + 26/26 Node** PASS sobre SHA de GitHub con `mixer_adapter` de árbol idéntico. **`stage_ready:false`**; runner Engine simulado en B11, fallback no ejecutado, cero producto/deploy. JM: revisión de contrato backend/Stage, registro Owner↔sesión, guía corta de sincronización sin reemplazar máster, reloj global waveform/listen/Edit/Export y fallback. E2E Mac largo de JM obligatorio antes de integración.
- **Benchmarks cerrados #265**: compresión Opus 96/64, caché/proxy, GOP y mini benchmark híbrido documentados como evidencia limitada; no activar CRF30, 64k, GOP remoto ni ASDMR sin paridad/medición E2E.
- **Otros pendientes de producto, fuera P0–P3:** #254 fallos Engine; #243/#252 miniaturas/primer Save; 360/multicanción E2E; release/actualización/firma Windows/Mac. No declarar MONTARA globalmente terminado.

## Próximo relevo
- FER ha entregado P0 corregido, contención P1, auditoría P2 y contrato de laboratorio P3. **No se han integrado nuestras PR abiertas ni cambiado servidores, los originales o Companion habitual** por estas entregas.
- Para dar salida al bloqueo: **JM revisa/integra #267 y mide A/A Mac**; equipos acuerdan lease #272, validación Windows #260 y puntos de acoplamiento #274; solo después PR de integración B11 en pequeñas piezas y E2E del producto.

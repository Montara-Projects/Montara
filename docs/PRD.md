# Montara — PRD y decisiones de producto

**Fecha de la decisión:** 22 de noviembre de 2026  
**Estado funcional:** MAIN aprobado por JM tras prueba humana.  
**Base de desarrollo compartida:** rama principal [main](https://github.com/Montara-Projects/Montara/tree/main).  
**Release de referencia:** 3862f60282617f1b55a035e25364ec865869072d (PR #382; paquete selectivo JM 20a201d257f8c720d3c3c608b050b18cdcae5636).  
**MAIN autenticado:** https://montara-main.memoriainvalida001.workers.dev

## Decisión de aceptación — MAIN aprobado

**Confirmación humana explícita del propietario JM (22/11/2026):**

> «Lo acabo de probar y está confirmado. De confirmación humana también aprobada. [...] Está todo aprobado».

Queda **aprobada y cerrada la aceptación humana de JM** para la promoción del Mixer y los controles de proyectos de LAB-JM a MAIN. No volver a solicitar a JM la misma prueba ya confirmada.

### Funcionalidad aprobada y promovida

- **Mixer**: voz principal, co-lead y coros, FX, paneo y delay sincronizado al tempo; previsualización y mezcla final (aceptación previa #350, reafirmada sobre MAIN).
- **Your Projects**: abrir proyectos y control de eliminación con confirmación, conservando exportaciones según contrato.
- **Conservado de MAIN**: sesiones de hasta 30 canciones, Stage y controles existentes, medio privado, Companion, aislamiento Owner y descargas con permisos.
- **Selección segura**: no se sustituyó MAIN por la interfaz entera de JM ni se incorporaron módulos experimentales.

**Evidencia técnica adicional** (distinta de la aceptación humana): 15 tests Mixer y 31 tests de sesión/audio/vídeo pasaron en el entorno Python de MAIN VM; pruebas Node de rutas de sesión, más salud MAIN HTTP 200, inicio OAuth 302 y recursos privados 401 sin sesión. Los servicios MAIN, JM, FER y BETAMAIN conservaron sus procesos tras merge. La validación humana es declaración expresa del propietario, no se presenta como una sesión grabada por este agente.

## FER: trabajar desde MAIN

**FER (@luccifer00) está habilitado para continuar el desarrollo desde la rama main ya aceptada por JM**. MAIN es la base común a partir de ahora.

Contrato:
1. Partir del SHA vigente de main, crear rama de trabajo y PR. No sobrescribir directamente los paquetes o datos de la instalación MAIN ni desplegar automáticamente cada commit.
2. Mantener funciones aceptadas de JM y las exclusivas de MAIN: Mixer, sesiones de 30 canciones, proyectos, Companion, Stage, permisos y rollback.
3. Ejecutar benchmarking y optimizaciones aisladas, sin interferir con sesiones de LAB-JM, LAB-FER o MAIN.
4. FER valida sus propias plataformas (incluyendo Windows/Companion). La aprobación de JM no se atribuye erróneamente a FER ni equivale a CI verde.

## Próxima prioridad — Proyecto Colibrí: velocidad

**Mandato de producto de JM:** «Más que un canario necesitamos un colibrí».

**Tarea de ejecución y benchmark FER/JM:** [#386 — Proyecto Colibrí](https://github.com/Montara-Projects/Montara/issues/386).

MAIN es funcionalmente aceptado; ahora queremos **velocidad percibida y real medible**, no solo estabilidad.

- **Medir antes de cambiar**: latencia p50/p95, esperas de red, tiempo de Engine, FFmpeg, cola, caché fría/caliente y tiempo total; misma muestra/hardware/build para comparar antes y después, con fer/JM y Mac/Windows.
- **Camino crítico**: abrir proyecto; Continue y «Listening to your videos»; ingest/proxy; 305 tomas y 360; hover; Edit y Save; Swap; preview Mixer; export/render y descarga.
- **Interactividad**: respuesta visual inmediata; progreso real por tarea (no porcentaje inventado), trabajos largos asíncronos e idempotentes con estado comprobable, sin bloqueo del navegador.
- **Metas iniciales propuestas, no resultados**: feedback visible inferior a 100 ms; Edit con datos cacheados inferior a 500 ms en condiciones controladas. Fijar objetivos de tiempo total y p95 después del benchmark A/A.
- **Calidad y seguridad intactas**: no degradar música/FX/vídeo; no detener procesos de otros propietarios ni tocar proyectos/cachés ajenos; no borrar originales; mantener rollback.
- **Definición de terminado por mejora**: números antes/después, reproducción, pruebas Mixer/Stage/30 canciones, y aprobación humana de UX/audio cuando proceda.

Priorizar y reutilizar #348 (IngestStage y progreso), #359 (Stage 409/503/latencia/Swap), #265 (medición FER), y PR #383 (Stage-JM todavía candidato). Mantener un único tablero de rendimiento para evitar trabajo duplicado.

## Separación de aprobaciones y pendientes técnicos

**Aprobación humana JM: APPROVED / DONE.** Esto no equivale automáticamente a:
- GitHub Actions habilitado, bloqueado por facturación #372.
- Certificación independiente de FER en Windows/Companion (#368).
- Activación de Stage experimental PR #383, cierre seguro Engine #305/#369, almacenamiento R2 #371 o cambios de proyectos #379/#380.
- Certificación de nuevas mejoras de rendimiento o despliegue indiscriminado.

MAIN es la base compartida aceptada y **FER puede trabajar desde ella**. Las mejoras se incorporan mediante rama + PR + QA + rollback, sin revocar esta aceptación humana.

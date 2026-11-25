# STATUS — laboratorio Chema / JM
Actualizado: 2026-11-25. Responsable JM. Corte Git, no comprobación nueva de runtime.

## Trabajo actual — #415, aportación de producto a CORE V2
- Ramas documentales/QA #415, desde main `7113fd2801558cc31bf9b2c1bfab360c7faa40ca`.
- Engine Git `9af275b18535005e36bd289a68ceb4a1d2f6c506`; Mixer `f15ff91c1b80fc5f157099dcd9451d958d553ae6`; sin cambiar submódulos.
- Leídos candidato ADR 7141340666, ACK FER 7150570278 y respuesta JM 7151607436.
- Propietario solicita comenzar tareas asignadas; JM inicia inventario producto/editor, recetas y criterios QA.
- FER lidera inicialmente Core/release/instalador; no desarrollar una implementación paralela de ese núcleo.
- Entrega: `docs/integration/CORE_V2_JM_PRODUCT_HANDOFF_415.md`.
- Diez grupos de componentes existentes clasificados; 34 rutas de código/pruebas comprobadas.
- Doce invariantes de producto y ocho escenarios de aceptación propuestos; revisión conjunta pendiente.
- Fixture Stage v1 sintética: seis segundos, dos fuentes, tres cortes, velocidad/luz por shot; roundtrip PASS.
- 22 pruebas existentes de receta/intervalos neutros PASS en Mac; 3 pruebas de render no seleccionadas.
- Comando: `python -m pytest tests/test_local_video.py -k 'recipe or neutral_interval' -q` en entorno temporal aislado.
- Sin instalar dependencias globales ni tocar los entornos de Companion.
- Hallazgo: validador nativo actual exige Stage/youtube; no demuestra soporte Push/Show ni envelope V2.
- Licencias/redistribución, fixtures audiovisuales V2 y adaptación de contratos permanecen pendientes.
- No se afirma E2E V2/Linux general, OAuth, benchmark ni instalación Mac a partir de estos tests de componentes.
- Repositorio V2, entorno, presupuesto y cambios compartidos siguen decisiones separadas; no aprovisionar.
- PR #416: inventario/receta. Lote siguiente: `tools/core_v2_media_fixture.py`, banco sintético + oracle + gate Linux.
- 9/9 tests nuevos PASS Mac: render real 6 s H.264 1080p/AAC, cámaras/tiempos/velocidad/máster y output recuperado.
- Evidence/hash/límites: `docs/integration/CORE_V2_JM_MEDIA_FIXTURE_415.md`; menos de 1 MiB sintético conservado fuera de Git.
- Engine exacto inicializado solo en scratch; Companions no intervenidos. Linux gate 45614403174: 22+9 PASS sobre código `1fb15f8`; no E2E V2.
- CI general #416: Stage/Push/Mix/Engine/container PASS; Session timeout detectando Companion, FAIL separado.
- Siguiente: resultado Linux del oracle y revisión FER del mapeo al contrato v0; no crear Core paralelo.

## Continuidad y límites
- Mantener V1 y P0 compatibles; Push/Show pueden avanzar en LAB sin cambios estructurales silenciosos.
- MAIN efectivo no se deduce de Git main; #392/#398 coordinan reconciliación de overlays y manifiesto.
- PR #412 conserva relevo operativo previo; esta actualización no certifica ni revoca sus evidencias de runtime.
- Trabajo local previo de beta/audio preservado fuera de este checkout; no mezclado en la rama de #415.
- Originales locales por defecto; cloud opt-in y desactivable. CORS/health no autentican Companion.
- MAIN, LAB-JM, LAB-FER, Work, proyectos, SQLite, brokers y Companions no modificados en este lote.
- Ninguna VM arrancada, compra, reinicio, migración, despliegue ni limpieza; rollback documental por revert.
- Coordinación técnica en #415 y #216; no confundir propuesta, prueba focalizada, merge y despliegue.

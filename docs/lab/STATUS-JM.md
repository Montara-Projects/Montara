# STATUS — laboratorio Chema / JM
Actualización de control: 2026-11-17 (GitHub; NO acredita despliegue o runtime). Responsable: JM.

## Montara Work — actualización operativa 2026-11-17 (fase 7C AUTORIZADA, NO EJECUTADA)
- **7B arranque verificado (informe Codex, #216):** VM existente `montara-test` (proyecto `montara-pruebas-10292226`, zona `europe-west3-a`, instancia `7500489339798713948`) RUNNING desde 13:37:02 CET; IP pública `35.242.225.127`, autoapagado activo. Recursos al inspeccionar: 41 GiB disco libre, 30 GiB RAM disponible y 8 vCPU. No se crearon recursos cloud nuevos.
- **Runtime observado:** LAB-JM :8101 Gunicorn, directorio `f05d6e9` y Engine del worker `92c7bc3`; LAB-FER :8102 directorio `78e9e67`, Engine worker `c89e779`; MAIN :8103 directorio `641fec3`, Engine worker `d844acd`. Mixers observados *en disco* JM/MAIN `f15ff91`, FER `c7a46a6`; los endpoints de versión dieron 401 sin sesión, por lo que estos datos no acreditan SHA/mezclador efectivamente servidos por HTTP.
- **Servicios existentes protegidos:** Owner legacy :8115, H4 :8116 y FER trial :8126 activos; Urano :8127 sin listener, URL pública 403 con TLS válido. Tres trabajos `running` y dos `orphaned` persistidos en ledgers H4/Staging/I26; cuatro sesiones vigentes Staging #236 y una FER trial. Sin FFmpeg/FFprobe observados en la inspección; **no recuperar, borrar ni alterar** trabajos o sesiones.
- **Multisong / Work:** HTTPS `https://multisong.35-242-225-127.sslip.io/` con certificado válido hasta 2027-02-14; responde **503 mantenimiento**, no Work operativa. Puerto interno `127.0.0.1:8128` libre en 7B. OAuth privado de Work aún no configurado; ruta de código `/urano/v1/google/callback` verificada, pero registro externo del callback completo y cuenta permitida **PENDIENTES**.
- **Autorización 7C expresa:** propietario autorizó crear Work **aislada** (portal, broker, sockets, SQLite, datos propios) en :8128 y conectar **únicamente virtual host Multisong** *después* de verificar OAuth exclusivo con una cuenta, aislamiento, salud HTTP/TLS y rollback. Ref: [#216 comentario 6948581619](https://github.com/amehcgracia-byte/Montara/issues/216#issuecomment-6948581619). **Autorización registrada ≠ implementación/activación**; a esta actualización no constan cambios de Nginx, OAuth, infraestructura ni despliegue 7C.
- **Companion / #251:** Mac habitual Companion 0.6.10, Engine `3e92908`, libre durante inspección 7A; no sustituir. [PR #260](https://github.com/amehcgracia-byte/Montara/pull/260) HEAD `689cb3e` **draft, no fusionada ni desplegada**: guardado Exports, Finder real, fallback Descargar y reintento sin render PASS en QA Mac; 30 Python/13 Node PASS. Windows nativo y reinicio integral Companion pendientes; CI Engine #254 separado. Una Companion QA debe usar perfil/puerto propios y pin compatible `92c7bc3` tras revisión del contrato.
- **Pendientes principales:** 7C ejecutar gates y publicar Work solo si pasan; prueba sintética real desde HTTPS (login → proyecto → Stage → Companion QA → dos Save shot → reapertura → MP4 Exports), #252 E2E autenticado LAB-JM aún bloqueado, #254 seis fallos Engine. No tocar Urano, LAB-FER, LAB-JM, MAIN, Companion habitual ni almacenamiento ajeno. Mantener rollback Multisong a 503, y documentar cualquier cambio efectivo.
- **Fuente y alcance:** inspección comunicada en [#216 6948270324](https://github.com/amehcgracia-byte/Montara/issues/216#issuecomment-6948270324) y autorización [#216 6948581619](https://github.com/amehcgracia-byte/Montara/issues/216#issuecomment-6948581619). Esta actualización es **documental desde GitHub**, no nueva comprobación por SSH.

---

## Estado vigente — corte GitHub main `4939c7d07a78b4df3b1c472a2fc1ab5e63dbb078`
- Coordinación: `docs/COLLABORATION.md`, issue #216. Cambios de código integrados ≠ desplegados; servicios/datos/gastos necesitan gate explícito.
- PR **#236 fusionada** squash en `457eebfc`, además de #246 en `42ee5ed`: H4 Owner/broker preflight y O1 control de unidad systemd ausente. No significa activar H4 ni recuperar ledgers reales.
- LAB-FER Windows / Companion: PR **#249** (origen LAB-FER autorizado), **#250** (baseline/handoff E2E) fusionadas; E2E humano Stage→Companion→MP4 Windows comunicado como PASS, sin acreditación de multicanción/Mac/MAIN.
- #252 (17-11): LAB-JM checkout f05d6e9/Engine 92c7bc3. Chromium aislado Mac, Stage 4f93894/Engine 92c7bc3: Edit 0 GET, primer Save 1 GET, segundo Save con cambio de cámara 0 GET de galería; 0 miniaturas ajenas cambiaron URL o bytes. Luz por toma PASS por HTTP. Linux VM: seis fallos #254 reproducidos. Sin despliegue; navegador contra LAB-JM servido y prueba humana FER pendientes. Fase 5B: 8101 respondió 401 Basic Auth; el proyecto activo es compartido por proceso y su selección se persiste. Sin navegador autenticado ni prueba sobre 8101. #252 abierta.
- **#251 abierta**: guardar exportación MP4 directamente en carpeta del proyecto vía Companion, contrato de diseño; no implementada.
- **#254 abierta**: CI `e2e(engine)` conserva seis fallos conocidos (light/framing/closeup), no declarar CI global verde ni borrar tests.
- PR **#247** (mapa de MAIN/runtime/rollback) y **#248** (informe offline de sesiones caducadas) siguen **draft abiertas**, no fusionadas ni desplegadas. MAIN :8103 checkout observado `641fec3`, pero SHA cargado/URL oficial/rollback quedan sin acreditar; pin publicado Engine `92c7bc3` y Mixer `f15ff91` no equivalen a proceso efectivo.
- Multicanción `0dfd083` permanece candidato **local no integrado en MAIN**: dos vídeos de 91 s y banco Linux local validados; sin E2E oficial HTTPS.
- Limpieza: fase 4D.2 del banco multicanción retiró 227 cachés sintéticas y recuperó 165,92 MiB; 394 archivos conservados, respaldos VM+Mac verificados. Fase 4E piloto histórico: 30.249 archivos auditados, 25 subidas (1,56 GiB) **protegidas** (13 vinculadas por symlink a sesiones, 12 de origen no acreditado); **0 GiB** adicionales aprobados para borrar. No tocar sesión `rendering`.
- Siguiente JM P0: validar primer Save shot y contraste `#252` con Engine/versiones fijadas; P1: revisar contrato `#251` e implementación sin perder renders; P2: decisiones de producto para seis fallos `#254`; P3: completar observaciones reales `#247` antes de anunciar MAIN beta.
- Investigación JM posterior (17/11): #252 causa RED/GREEN establecida pero prueba visual humana pendiente; criterio de aceptación y plan sin deploy en issue #252. #251: inspección de `companion/video_jobs.py` demuestra MP4 ya escrito en raíz del proyecto; faltan subcarpeta `Exports/`, apertura autorizada, UX y tests, ver comentario issue #251. #254: propuesta de criterio por toma y paridad preview/export; seis fallos Engine siguen abiertos, sin nueva ejecución CI. Estas tres actuaciones son solo inspección/coordinación GitHub, **no corrección desplegada**.
- Evidencias: issues #216, #251, #252, #254, PR #236/#243/#249/#250/#253. `STATUS-FER.md` lo mantiene FER; no modificarlo desde JM.

---

## Registro histórico de JM (corte anterior, 2026-11-16)

Actualizado: 2026-11-16. Responsable: equipo de Chema. Estado informado desde pruebas JM; no equivale a despliegue.
- Coordinación: docs/COLLABORATION.md (16-11), issue #216. Verde autónomo; ámbar revisión cruzada previa a merges/deploy de contratos; rojo autorización humana para infraestructura/datos/gastos.
- GitHub main HEAD comprobado antes de esta edición: e92422643770e27f95d482ab175846c447a0aa27 (#244).
- Main pin publicado: Engine 92c7bc33f59baae92a8d61e5dd4bf0ce9685d79e; Mixer f15ff91c1b80fc5f157099dcd9451d958d553ae6.
- Commits #237–#242 integrados en main; #236 preflight H4 y #243 diagnóstico de miniaturas permanecen abiertos según último control.
- STATUS-JM anterior (07-11) era histórico: se sustituye por estado actual, sin borrar su historial de Git.
- Trabajo JM de fin de semana: integración multicanción en ramas locales aisladas, NO en main; candidato integrado local 0dfd083.
- Referencias declaradas de candidato: Stage 79902b0, portal e0b8cd6, Engine 34c338d, Mixer f15ff91.
- Estado de publicación de esos SHA: candidato local validado en Linux; no consta rama remota accesible para 0dfd083 ni comparación completa de ancestralidad; pendiente publicar refs y diff, sin sobrescribir pines main.
- Sesión de prueba: un proyecto de 182 s, 2 cámaras continuas, 2 pistas WAV, dos canciones 0–91/91–182 s, sus propios másteres/planes/exports.
- Prueba local: dos MP4 de 91 s H.264 1920×1080/AAC, movimientos/keyframes 360 diferentes, cámara 2 desde segundo 91, ffprobe y decodificación completa PASS.
- Render local verificado: 212,2 s canción 1 y 236,7 s canción 2; audio de cada máster con desfase medido 0 ms en muestra.
- Banco Linux: 45 pruebas audiovisuales PASS, hash de ambas descargas correcto tras reapertura, propietario ajeno y CSRF inválido rechazados.
- Importación/detección/canciones: 20 pistas simultáneas y conservación de másteres verificados en bancos anteriores; no reclamar E2E HTTPS por ello.
- Commits de subida: 368bbe3, 6cd9ad3, 497436d (finalize reintentos/idempotencia).
- Commits sesión/mezcla: 5d771d5, f4ab172, 54dff74, 7672e04, d145a65, 8ecb1a5.
- Commits por canción/render: 24f27d6, cd1a208, 332b1e9, c4650d6, a7b3900, d963261, 32d22a4, 831074b.
- Commits edición y 360: 80ff5e1, 4bf0600, 08e186b, 41935e7, c2bed02, 79902b0, e0b8cd6, 34c338d.
- Alcance anterior: algunos SHA son de repo Engine zucker_videos y otros de ramas locales Montara; ubicación/ancestralidad individual aún por verificar en GitHub. No fusionar a ciegas.
- Staging multicanción: hostname https://multisong.35-242-225-127.sslip.io/ y certificado TLS preparado; sitio 503 de mantenimiento, candidato no instalado.
- Puerto previsto staging 8128; servicio Urano 8127 separado. Falta OAuth exclusivo de staging y callback /urano/v1/google/callback.
- Urano/H4 no equivalen a staging multicanción. H4 Windows/Companion de FER pasó E2E humano propio; no demuestra función multicanción ni Mac.
- VM Google Cloud montara-test, IP estática 35.242.225.127; disco recuperó 41,81 GiB al limpiar medios de prueba autorizados de Main/JM y WAV expandidos de staging.
- Último espacio libre reportado 42,48 GiB (medición tras validación); FER observó ~43 GiB en su revisión; no ampliar ni contratar recursos.
- Autoapagado montara-idle activo; mejora de actividad de Urano reportada, pero I6b/I6c no activados conjuntamente en watchdog/broker desplegados.
- Limpieza automática de proyectos efímeros Main/JM, confirmación descarga, control admisión y recuperación de arranque: PENDIENTES; prohibido borrar datos ajenos.
- Riesgos integracion: conflicto de pines Engine entre main/Companion Windows/candidato; revisar API, origins, proyectos/canciones, seguridad y compatibilidad.
- Hallazgos FER: huérfano I26 legacy distinto del H4 ya reconciliado, posible fallo stop_verified ante unidad not-found; pruebas mock no prueban causalidad del apagado.
- Hallazgo FER: /ensure 503 H4 por roots distintos de broker I26 vs H4; PR #236 propone broker dedicado. No cambiar rutas/ledger sin revisión.
- Errores Google/Show comunicados por Windows son históricos sin correlación vigente; se requieren URL/hora/logs si reaparecen.
- Próximos pasos P0: publicar refs reproducibles y diff contra main; contrastar contrato Companion Win/Mac y reconciliar PR #236/O1 antes de alterar shared.
- Próximos pasos P1: activar staging multicanción solo con OAuth/rollback/espacio adecuados, probar HTTPS con cuentas reales.
- Próximos pasos P2: limpieza efímera probada en Main/JM; no eliminar export antes de descarga confirmada; conservar autoapagado.
- Fuente de coordinación: responder y acusar recibo en issue #216; una PR funcional se integra en main solo después de tests y revisión, nunca por frecuencia a costa de estabilidad.

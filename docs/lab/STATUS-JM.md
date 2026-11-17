# STATUS — laboratorio Chema / JM
Actualización de control: 2026-11-17 (GitHub; NO acredita despliegue o runtime). Responsable: JM.

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
- Montara Work 7B: VM arrancada con autorización, Multisong TLS válido/HTTP 503, 8128 libre, OAuth propio ausente. Callback validado en código. 7C autorizada en #216; ambos callbacks del cliente compartido ya abren Google; Work requiere confirmar su cuenta única y probar el intercambio real antes de publicar. Sin cambios de infraestructura. Companion Mac 0.6.10 usa Engine 3e92908; #260 en revisión.
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

### Montara Work 7C — 2026-11-17

- Lista privada de cinco cuentas confirmadas, guardada exclusivamente para Work con permisos 0600. Preflight de configuración OAuth del candidato aprobado con el cliente existente y el callback Multisong. El intercambio real y la creación de sesiones están pendientes.
- El puerto 8128 estaba libre y Multisong devolvía HTTP 503. Pendientes el portal y broker dedicados, persistencia, prueba de reversión y comprobación de aislamiento y rechazo con identidades reales. Se mantiene el 503.

### Montara Work 7C — portal y backend integrados

- Candidato 0dfd083, Engine 34c338d, Mixer f15ff91, Stage 79902b0 y portal e0b8cd6 instalados en Work. Portal Gunicorn en 127.0.0.1:8128, broker, sockets, ledger y SQLite propios. Cuenta de sistema exclusiva y cinco cuentas Google permitidas. La credencial Work está en un archivo dedicado y privado.
- Salud 200, ruta nativa sin sesión 401, inicio OAuth 302 y host incorrecto 403. Preflight del broker real y del montaje Owner de solo lectura aprobado. Cinco proyectos sintéticos persistieron tras parar y arrancar solo Work, con 20 lecturas cruzadas rechazadas en el catálogo. Siete pruebas adicionales de OAuth sintético y aislamiento del broker aprobadas.
- Multisong sigue en 503. Pendientes el intercambio real con Google, creación de sesiones de las cuentas, rechazo real de una sexta cuenta y recorrido de proyectos desde el navegador. El código probado por el banco sintético no equivale a esas pruebas.
- Reversión interna ensayada: parar solo montara-h4-work-portal y montara-h4-work-broker cuando estén libres. Se libera 8128 y desaparece el socket de admisión. Arrancar el portal recupera también el broker y conserva SQLite. Nginx sigue con la configuración pública original.

### Montara Work 7D — entrada HTTPS privada

- Portal y broker activos. Entrada TLS de prueba en loopback de la VM, accesible desde el Mac por SSH y un perfil dedicado de Brave con el hostname exacto del callback. Salud HTTP 200 con certificado comprobado. Nginx público conserva HTTP 503.
- Pendientes la acción interactiva de Google, la comprobación de sesiones y logout, y el aislamiento con cinco identidades reales y una sexta sin autorización. Se conserva la evidencia sintética de 7C.
- Para retirar la entrada de prueba, cerrar el túnel SSH dedicado y parar la instancia Nginx de /run/montara-work-7d con su propia configuración. El portal, broker y datos de Work se conservan.

- Seguimiento 7D: recuperado el túnel del Mac como proceso de su sesión gráfica. HTTPS privado responde 200 y la portada pública conserva 503. Los recuentos de Work muestran cero identidades y cero sesiones; queda pendiente el primer login interactivo.

- Work 7D: una identidad y una sesión reales verificadas mediante recuento privado tras el login confirmado en Brave. Pendiente el aislamiento con varias cuentas reales.
- Companion Work: el HTML original apunta a las rutas de versión y descarga de JM, ausentes del portal Work (404). La entrada HTTPS privada devuelve ahora 503 explícito. El paquete histórico es sin firma y el instalador estándar comparte el puerto y la instalación habitual; queda pendiente construir y probar un paquete QA aislado alineado con Engine 34c338d. Multisong público sigue en 503.

### Montara Work — acceso normal y Companion QA

- Multisong público verificado: HTTP 503 y mensaje de editor pendiente. HTTPS privado devuelve salud 200 y el primer login Google real está confirmado. Se abrió un segundo perfil privado para validar otra cuenta sin mezclar cookies. Publicación pendiente de aislamiento real, rechazo de una cuenta no autorizada y comprobaciones de sesión/logout/CSRF.
- Las cuentas Linux sin login interactivo montara-work y montara-work-ops pertenecen a grupos exclusivos. montara-work ejecuta Gunicorn y es propietario del catálogo, sesiones y raíz Owner. montara-work-ops identifica al interlocutor de operaciones por UID en el socket de control del broker; no ejecuta el portal. El broker corre como root y verifica el UID del interlocutor; el portal usa un socket de admisión separado. No se alteraron las cuentas.
- Construido candidato macOS QA 0.6.10.1, fuente 0dfd083, Engine 34c338d, app y datos QA propios, puerto 47828 y origen exacto de Work. SHA-256: 1fc8aedcf0ac6324f5df642ff1119dc063ee54820038cb9cd94cce4ae7c79d3a. Paquete sin firma; pendientes validación de arranque y distribución. Companion habitual 0.6.10 sigue respondiendo en 47820. PR #260 sigue abierta y se mantiene como carril de revisión independiente.
- Reversión QA del candidato: cerrar exclusivamente el proceso QA, retirar la app Montara Work Companion QA y conservar su directorio independiente de Application Support hasta decidir si se necesitan sus datos. No usa el LaunchAgent habitual.

### Work — acceso y menú de cuenta

- Antes del cambio, el túnel privado entregaba el 401 generado por Work al abrir la ruta nativa sin sesión. La portada privada iniciaba OAuth por 302 y Multisong público servía la página de mantenimiento 503.
- Menú de cuenta c9467d1 activado en el portal privado mediante un drop-in de Work. La navegación HTML sin sesión ahora inicia OAuth; las rutas privadas de datos siguen protegidas. Perfil Google por sesión, listado de proyectos por workspace, cambio de cuenta y logout con origen exacto, CSRF, revocación y expiración de cookie.
- 14 pruebas Linux aprobadas, incluidas revocación, cookies y rechazo de CSRF ajeno. Pendiente prueba real del menú con dos perfiles, aislamiento cruzado y rechazo de una cuenta no autorizada. Multisong público sigue en 503.
- Rollback interno: desactivar solo el drop-in 20-account-menu.conf, daemon-reload y reinicio exclusivo del portal Work cuando esté libre. La columna SQLite de perfil es aditiva.

- Work menú minimalista 84f1d70: avatar o iniciales, popover nativo, diálogo y búsqueda de proyectos adaptados de FER #189, Settings visible cuando los ajustes de audio están disponibles. El menú usa las sesiones y rutas Work existentes. Rollback: restaurar el drop-in previo guardado como rollback.conf en el directorio de la revisión y reiniciar solo el portal Work.
- Salud privada comprobada. El propietario confirmó dos accesos OAuth autorizados con la versión anterior. Inspección visual de la revisión nueva pendiente por timeout del control de Brave. Pendientes pruebas cruzadas reales y rechazo de una sexta cuenta. Multisong público conserva 503.

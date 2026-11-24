# Montara — colaboración entre laboratorios

Acordado el 30-10-2026 por José Manuel (Chema) y Fernando. Esta página es la norma; `docs/lab/` es el estado.

## Responsables principales (no exclusivos)

| Equipo de Chema (`main`, `claude/*`, `codex/*`) | Equipo de Fernando (`fernando/continuacion-montara`) |
|---|---|
| Desarrollo e integración del producto | Investigación y optimización de rendimiento |
| Stage, Show, Mixer y experiencia de usuario | Proxies, cachés, acceso a archivos locales y transferencia selectiva |
| Flujo de subida y continuidad de la edición durante las transferencias | Arquitectura híbrida local/servidor/GPU y futuro companion Windows/macOS |
| Validación E2E y decisión de qué entra en `main` | Benchmarks reproducibles, compatibilidad y documentación de resultados |

**Área compartida:** subida y edición durante la transferencia. Antes de desarrollar en ella, leer la familia «Subida, proxies, acceso local y transferencia selectiva» de `docs/lab/INVENTORY-FER.md`.

Ambos equipos pueden investigar, proponer y revisar cualquier cosa. Una observación técnica no autoriza a modificar el otro laboratorio.

## Fuentes de verdad

- **Código y resultados:** ramas y PR de GitHub. Entire y las transcripciones de agentes no los sustituyen.
- **Estado:** `docs/lab/STATUS-JM.md` y `docs/lab/STATUS-FER.md`. Cada uno tiene 40 líneas como máximo y lo sobrescribe su propio laboratorio en cada hito.
- **Inventario:** `docs/lab/INVENTORY-FER.md`. Indexa los experimentos de Fernando por familias. Se audita una vez y después se mantiene de forma incremental.
- **Tiempos:** `docs/lab/RUNS.md` (tabla) y `docs/lab/runs.jsonl` (registros) guardan cada trabajo medido con fecha, versiones, máquina y segundos por fase. Solo se comparan filas con el mismo motor y la misma máquina.
- **Avisos:** el workflow `Lab digest` publica cada rango de commits nuevo de `main` y de `fernando/continuacion-montara` en un issue fijo por rama. Es determinista: no depende de que ningún agente se acuerde.

## Presupuesto de lectura para agentes

1. Empezar por esta página y los dos STATUS.
2. Después, `git log --oneline --no-merges <último-revisado>..origin/<rama>` y `git diff --stat` del mismo rango.
3. Los informes largos solo se abren al decidir sobre esa pieza.
4. Una revisión responde A–E en una pantalla como máximo:
   - **A.** novedades
   - **B.** duplicidades
   - **C.** reutilización
   - **D.** riesgos de integración
   - **E.** recomendaciones

   Si no hay nada, responde «sin cambios relevantes».

## Estados de madurez

`investigado` · `implementado` · `validado-lab: <comando exacto>` · `candidato` · `integrado: PR #n` · `validado-producción`.

Una funcionalidad del producto solo está «terminada» cuando `tests/e2e_journey.py` pasa en Linux y alguien ha mirado sus capturas (ver `CLAUDE.md`). Un benchmark útil sigue siéndolo sin E2E; simplemente no se presenta como funcionalidad.

## Git

- **Chema decide e integra en `main`** sin esperar autorización del otro laboratorio. Basta con informar: el issue «Lab digest · main» lista los commits, y el laboratorio de Fernando señala riesgos si los ve.
- Nadie modifica la rama `fernando/*` sin coordinarlo con Fernando.
- La integración se hace pieza a pieza, como en la PR #8: rama corta desde `main` y una PR por pieza. La rama experimental nunca se fusiona entera.
- Cada PR indica los commits de `engine/` y `mixer/` y las pruebas exactas que se ejecutaron.
- Un cambio de submódulo demuestra `git merge-base --is-ancestor <viejo> <nuevo>` o declara qué se pierde. Los cambios del motor pasan por `zucker_videos` (ver `CLAUDE.md`).
- Nada de `git push --force` para sincronizar.
- Solo se comparan resultados con el mismo motor, el mismo mezclador y el mismo tipo de máquina, con la salida de `deploy/vm/manifest.sh` adjunta.

## VM compartida

- Un usuario Linux por laboratorio. Los servicios escuchan solo en `127.0.0.1`.
- El trabajo pesado pasa por `montara-bench <experiment_id> <comando>`.
- Nadie toca el HOME ni los servicios del otro laboratorio.
- Cada acción de administrador (`sudo`) queda en una línea de `docs/lab/VM_LOG.md`, con quién la autorizó.

## Secretos

**Los repositorios Montara, zucker_videos y ZuckerMixer son públicos.** Todo lo que se sube, los issues y los logs de Actions los puede leer cualquiera.

- Nada de contraseñas, tokens, llaves, rutas privadas ni transcripciones de agentes en Git, issues o Entire.
- Una contraseña que ha pasado por un chat se cambia.
- El acceso a GitHub desde la VM usa una credencial limitada a este repositorio, no una llave personal.

---

## ACUERDO OPERATIVO ENTRE LAS DOS IA — 16 de noviembre de 2026

> **LECTURA OBLIGATORIA PARA LA IA DE CHEMA Y LA IA DE FERNANDO.** Esta sección amplía, no deroga, el acuerdo original del 30-10. Fernando ha aprobado expresamente la coordinación previa de cambios compartidos y ha solicitado que **toda comunicación técnica entre IA ocurra en GitHub**. El canal permanente de interlocución es [issue #216](https://github.com/amehcgracia-byte/Montara/issues/216); este documento define reglas, cada equipo actualiza únicamente su propio STATUS y las PR registran entregas. **IA de Chema: lee esta sección completa, responde al issue #216 y actualiza STATUS-JM.** No dependamos de que los humanos copien mensajes entre chats.

### 1. Fotografía CONSTATADA, no memoria de una IA

- **HEAD de GitHub main comprobado a 16-11-2026:** SHA completo 4bf32dc3a0f7b8d6ac43ad3a30bf7c70ce461d14. El HEAD 775bd88 del informe de Chema es **histórico**. No asumir que una rama de pruebas, un candidato local o un servicio desplegado son main.
- **Pines en main comprobados:** Engine 92c7bc33f59baae92a8d61e5dd4bf0ce9685d79e; Mixer f15ff91c1b80fc5f157099dcd9451d958d553ae6.
- **PR del 16-11 ya fusionadas en main:** #237 (evitar duplicar proyectos al reintentar carpeta), #238 (Companion Windows nativo), #239 (regresión obligatoria en CI Windows), #240 (comprobaciones de certificado y hashes del paquete de QA), #241 (ventana con texto escalado), #242 (E2E Windows/hosting y handoff a Chema). Ver enlaces al final.
- **PR abiertas comprobadas:** #236 (preflight H4 Owner/broker/SQLite) y #243 (test diagnóstico del primer Edit y miniaturas; NO es fix de runtime). No fusionar por simple antigüedad. **#229, #230, #232 y #234 figuran cerradas**: verificar expresamente merge/ancestro de código antes de afirmar que todas están aplicadas. #229 = cierre/admision; #230/#232 = Companion CI/runtime; #234 = aislar seis fallos heredados de Engine en CI, NO corregirlos por sí mismo.
- Este corte es fechable y caduca al moverse main: **consultar siempre nuevos SHAs, PR y versiones cargadas antes de actuar**.

### 2. Estado DE FERNANDO: qué ha pasado de verdad y qué no

**PASS E2E HUMANO Stage Vídeo H4/Windows 10, 16-11:** Google real → proyectos privados → Restore files → elegir carpeta local → seleccionar pista → sincronizar → proxies pequeños → editor y Edit/Save shot → render usando servicio Windows empaquetado → Download MP4. Se verificó el proceso real Montara.Companion.Service.exe escuchando en localhost 127.0.0.1:47820, en vez de Python manual en PowerShell; protocolo local 0.6.10, FFmpeg OK, Engine del Companion b867b3c72af8fe4685b487bcf1e09ffcc2a7c82b. **Este SHA de Companion difiere del pin Engine main: NO cambiarlos a ciegas.** Había actividad local durante render y VM ~25 % CPU; eso no prueba por sí solo cuánto trabajo hizo cada máquina. La descarga existió, pero la última prueba no registró explícitamente la reproducción completa del MP4.

**Alcance:** un modo de Stage, un Windows real, **web H4** y su backend privado; no certifica multicanción, Mac, Urano, Show, Push, Music, el servicio Linux denominado Main ni el instalador comercial. Código integrado por PR ≠ desplegado y validado en todos los entornos.

**Pendientes:** al primer Edit/Save shot se observó recarga visible de ~120 imágenes, pese a soluciones previas de Engine (commits históricos c9c919d, 69bd9b7, 12ec8fe, 7c728c6). PR #243 incorpora un test de refetch al abrir el editor y sigue abierta: separar peticiones HTTP, invalidación de caché y trabajo FFmpeg antes de reparar. UX del MP4 local: Mostrar archivo/Abrir carpeta además de Download. Firma Windows confiable, actualización manual segura y rollback pendientes; MSIX de QA autofirmado no es un instalador para usuarios finales. Handoff detallado: [E2E Windows para Chema](https://github.com/amehcgracia-byte/Montara/blob/main/docs/integration/I5B_STAGE_VIDEO_WINDOWS_E2E_CHEMA_HANDOFF_2026-11-16.md).

### 3. Estado DE CHEMA: reconocer avance y diferenciar evidencia

Según **los informes de Chema recibidos 16-11, no comprobación nuestra de despliegue**, candidato local multicanción 0dfd083 con Stage 79902b0, Portal e0b8cd6, Engine 34c338d y Mixer f15ff91. Prueba local declarada: proyecto de 182 s, dos cámaras y dos pistas WAV, dos canciones de 91 s con másteres/mezcla/planos/movimientos 360 independientes, persistencia, y dos MP4 H.264 1080p/AAC; tiempos de render 212,2 y 236,7 s. **Este es un éxito de laboratorio, no un E2E HTTPS desplegado.** No desautorizarlo ni presentarlo como integrado en main.

Los informes citan reparaciones de /finish concurrentes (368bbe3, 6cd9ad3, 497436d), sesiones multipista (5d771d5, f4ab172), caché librosa/Numba (54dff74, 7672e04), persistencia de másteres (d145a65, 8ecb1a5), Stage multicanción, identidad de canción y movimientos 360. **IA de Chema: confirma repos/rama, ancestralidad y qué commits están o no en main**, sin suponer que Fernando haya leído tus cambios locales. Fernando hará lo mismo con nuestras PR.

**Dependencia de producto a revisar antes de optimizar:** una actuación = un proyecto = N canciones = N másteres/planes/renders. Contrastar API, IDs, offsets cámara (tiempo absoluto canción + tiempo editor - offset cámara), selección de canción, recuperación y contratos Companion Windows/Mac. Integrar por partes con tests de no pérdida de proyectos originales; no sustituir Engine/Mixer fijados masivamente.

### 4. UNA infraestructura, VARIAS entradas/servicios: no mezclar capas

| Referente | Qué sabemos | Qué no se debe inferir |
|---|---|---|
| Git main | Código y submódulos fijados | No garantiza que cualquier servicio corra ese SHA |
| Google Cloud VM compartida montara-test | Infra Linux, IP estática reportada [GCP_VM_IP], Nginx/servicios diferenciados | No presupone Vercel ni Cloudflare como backend |
| https://legacy-vm-host.invalid/urano/v1/native/ | Entrada Urano sobre sslip.io/Nginx según Chema | No equivale a web H4; un 502 puntual no revela la causa |
| https://montara-owner-h4.memoriainvalida001.workers.dev/ | Entrada privada H4 en Cloudflare Workers con backend VM y Companion Windows probado | No es contrato universal de hosting |
| Main (servicio Linux), JM, FER, broker H4, Staging | Procesos/usuarios/rutas distintos | No confundir servicio Main con rama main |
| Companion | Protocolo localhost 47820 y originales locales | Windows y Mac actuales son ambos temporales; unificar protocolo, no imponer una misma implementación OS |

**Acoplamientos reales a resolver:** el launcher Windows Program.cs fija BetaUrl H4; BundledService.cs limita MONTARA_COMPANION_ORIGINS a H4/Owner y localhost; UpdateDiscovery.cs confía en feed H4. Por tanto la web native de Chema no funcionará automáticamente con el mismo paquete. Diseñar configuración explícita, segura y verificable para entornos aprobados, con orígenes HTTPS exactos, **sin CORS wildcard, desactivar CSRF ni aceptar actualizaciones de dominios arbitrarios**. La web podría alojarse en Vercel, Cloudflare u otro servicio; las APIs/Owner, VM y DNS pueden ser capas distintas. **No migraciones duplicadas** de proveedor sin acuerdo previo.

**Dos incidencias de Windows/Urano citadas por Chema, NO declararlas actuales sin reproducción:**
1. Google authentication unavailable or denied: determinar URL exacta, fecha/hora, usuario autorizado (sin publicar correo), callback/redirect URI OAuth, cookies/sesión/CSRF y logs de rechazo. HTTP 302 hacia Google no demuestra login exitoso.
2. Lost the connection (/montara/show/examples): correlacionar VM encendida/apagada, Nginx, portal, broker, worker, endpoint, logs y HTTP en el momento del fallo. Un cierre de VM y un fallo OAuth no son el mismo error.
En H4 Windows se autenticó y completó E2E después; **esto no certifica Urano ni invalida los fallos históricos**. No culpar al navegador/Windows sin pruebas. No desactivar autenticación, controles de propiedad, CORS ni CSRF para salir del paso.

### 5. VM, datos, autoapagado y coste: evidencia actual por encima del informe

**Lectura fresca SSH 16-11 en la VM:** df -h / = **96 GiB total / 54 GiB usados / 43 GiB libres / 56 %**. Contradice el **99 % y 1,9 GiB libres** de los mensajes anteriores: quizá hubo limpieza o cambió el estado; NO inferir causa sin auditoría. Repetir df/du fechados y clasificar propietario, retención, temporales, renders y copias antes de afirmar que necesitamos disco. No borrar archivos, WAV, carpetas de usuario o .part ajenos a ciegas.

En la misma comprobación, montara-idle.timer está activo; montara-idle.service figura inactivo entre ejecuciones del timer (no implica que el autoapagado se haya deshabilitado). Montara-main y unidades H4 staging236 portal/broker/worker figuraban activas en esa instantánea: **no prueba que el login HTTPS de Urano funcione ni que PR #236 esté integrada**. Conservar el autoapagado por créditos y no alterar unidades shared sin acuerdo.

**Coste:** CERO nuevos cargos bancarios autorizados. No contratar disco/recursos ni migrar infraestructura porque haya créditos promocionales sin verificar saldo, caducidad y facturación real. Antes agotar limpieza segura, sin tocar datos ajenos; sin aprobación de los responsables, NO ampliar. No detener renders ni apagar servicio de otro dueño. Registrar cualquier acción administrativa autorizada en docs/lab/VM_LOG.md. No compartir secretos, cookies, tokens ni datos privados en issues o CI.

### 6. PROTOCOLO PERMANENTE DE IA A IA

**ANTES DE CADA BLOQUE DE TRABAJO:** leer CLAUDE.md, AGENTS.md, este documento, STATUS-JM, STATUS-FER e issue #216; consultar HEAD actual de origin/main, PR abiertas, submódulos y commits desplegados del servicio afectado. La IA de Chema mantiene **solo STATUS-JM (máx. 40 líneas)**; la IA de Fernando mantiene **solo STATUS-FER (máx. 40)**. No editar ni reescribir el STATUS de otro.

**VERDE — autónomo:** investigación solo lectura, benchmark aislado, tests, documentación propia, mejoras pequeñas que no alteren contratos ni servicios compartidos. Hacer y notificar con SHA/PR y evidencia sin pedir permiso innecesario.

**ÁMBAR — aviso y revisión cruzada PREVIOS a fusionar/desplegar:** cambios del pin o API Engine/Mixer, estructura de proyecto/canciones/recetas, Companion/orígenes/feed/updater, Owner/login/CSRF, Stage, Nginx/broker, rutas, workers, colas y contrato de originales/proxies. Publicar en issue #216 la diferencia propuesta, base/head/pines, dependencias, pruebas, rollback y pregunta específica. No es veto general ni exige autorización para cada microfix; es un mecanismo contra incompatibilidades. **Chema lidera main según acuerdo original; Fernando tiene autorización posterior para integrar piezas acordadas. Ambos respetan revisión cruzada.**

**ROJO — autorización humana explícita ANTES de ejecutar:** reiniciar/deplegar servicios ajenos, migrar datos, borrar medios/copias, cambiar DNS/firewall/systemd compartido, desactivar seguridad o autoapagado, subir originales sin consentimiento o gastar dinero. Registrar quién autorizó, alcance, backups/rollback. Una IA no se autoriza a sí misma.

**Toda PR** con potencial de integración indica A novedades / B duplicidades / C reutilización / D riesgos / E recomendaciones, SHAs viejos/nuevos de submódulos, pruebas exactas y tipo de PASS (lab / Git main / HTTPS real / Windows / Mac), seguridad, cambio de contrato, despliegue y rollback. Nada de merges de laboratorio enteros ni force-push. Si cambia Engine/Mixer, probar ancestralidad o declarar commits potencialmente perdidos. Si una IA no ha contestado, seguir trabajo verde aislado; **bloquear solo la fusión/despliegue ámbar afectado**, no paralizar todo Montara.

**CANAL OFICIAL:** avisar, preguntar, responder y cerrar decisiones **en issue #216 de GitHub**, o issue técnica enlazada con síntesis en #216; ningún agente puede afirmar que el otro sabe algo solo porque esté en un chat o documento nuevo. Cada IA acusa recibo (ACK) del aviso relevante, sin humano como mensajero. Asuntos de seguridad/datos personales se documentan redactados.

### 7. Plan coordinado y puertas de aceptación

1. **P0 — sincronizar antes de desarrollar contratos:** Chema/IA reconoce últimos merges y Fernando reconoce candidato multicanción; conciliar main, PR #236/#243, pines, deltas del candidato 0dfd083, impacto por servicios y API. No sustituir piezas por SHA a ciegas.
2. **P1 — infraestructura y errores solo si vigentes:** nueva medición de disco, comprobar autoapagado, rutas Nginx y servicios; reproducir Google/Show con URL/tiempo/HTTP/logs y diferenciar fallo de sesión de VM caída. Nada destructivo, nada de cargos.
3. **P2 — multicanción:** comprobar candidato en Linux aislado con sus dependencias, luego Staging acordado sin tocar JM/FER/Main/H4; E2E HTTPS Google real dos canciones/másteres/planes, reapertura, 360, render y descargas privadas. Test real de Companion Windows y de Mac por separado; no dar por completado multiplataforma hasta pasarlo.
4. **P3 — rendimiento:** cerrar diagnóstico de primeras ~120 miniaturas (PR #243 + fix y regresión); optimizar dos problemas comunicados por Chema: Listening to your videos y preparación/transferencia de 13 pistas (histórico reportado ~72:49 y ~2,03 GB de medios ligeros, **repetir medida**). Medir CPU/RAM/IO/FFmpeg por fase con SHAs fijos; no fabricar una segunda arquitectura.
5. **P4 — releases:** convergencia del protocolo Companion, firma persistente Windows y Mac notarizado, actualización **a demanda y con consentimiento**, sin actualizar durante trabajos y con rollback, y UX Mostrar archivo MP4. Referencia: [I5a política de distribución](https://github.com/amehcgracia-byte/Montara/blob/main/docs/integration/I5A_COMPANION_CROSS_PLATFORM_RELEASE_HANDOFF_2026-11-13.md).

### 8. Lo que debe contestar la IA de Chema EN GITHUB (#216)

Por favor, publicar una respuesta técnica con **ocho verificaciones** (hechos vs hipótesis):
1. ACK de lectura y HEAD/pines de main actual; actualizar únicamente STATUS-JM.
2. Qué PR de #229/#230/#232/#234/#236 y #237–#243 están integradas vs solo cerradas/abiertas vs desplegadas.
3. Rama/repos/ancestralidad del candidato multicanción 0dfd083, archivos, pines y diferencias con nuestro main y Companion.
4. Inventario de URLs/servicios/upstreams y SHAs **servidos** en Urano, H4, Main, Staging, JM/FER; qué se comparte y qué no.
5. Estado de disco **actual** y fecha, impacto para staging; ninguna propuesta de cargo sin verificación/permiso.
6. ¿Siguen ocurriendo ahora los errores Google y /montara/show/examples? URL, hora, HTTP y logs correlacionados sin secretos; si son históricos, etiquetarlos.
7. Contrato por canción que deben implementar o adaptar los Companions Win/Mac y gates de aceptación E2E.
8. Aceptación o enmiendas concretas al semáforo verde/ámbar/rojo y al canal GitHub #216, dejando escrito quién responde y cuándo antes de un merge ámbar.

**Conclusión de coordinación:** son dos avances complementarios — Stage Vídeo E2E Windows H4 real + multicanción local real —, NO dos productos distintos ni el mismo despliegue. **Un solo barco, un solo contrato y un solo lugar donde las IA se hablan.**

### Enlaces

- [Issue permanente #216](https://github.com/amehcgracia-byte/Montara/issues/216)
- [PR #236 abierta — preflight H4](https://github.com/amehcgracia-byte/Montara/pull/236)
- [PR #243 abierta — miniaturas Edit](https://github.com/amehcgracia-byte/Montara/pull/243)
- [PR #242 fusionada — handoff Windows Stage](https://github.com/amehcgracia-byte/Montara/pull/242)
- [PR #237](https://github.com/amehcgracia-byte/Montara/pull/237), [#238](https://github.com/amehcgracia-byte/Montara/pull/238), [#239](https://github.com/amehcgracia-byte/Montara/pull/239), [#240](https://github.com/amehcgracia-byte/Montara/pull/240), [#241](https://github.com/amehcgracia-byte/Montara/pull/241).

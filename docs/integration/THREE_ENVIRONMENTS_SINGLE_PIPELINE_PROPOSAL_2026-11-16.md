# Montara — propuesta FER/JM: una beta main + dos laboratorios, un pipeline (16/11/2026)

**ESTADO: propuesta ámbar, no acordada ni desplegada.** Coordinación oficial: issue #216. Objetivo de producto pedido conjuntamente por Fernando y Chema: un único enlace de beta que ejecute una release derivada de main; dos laboratorios independientes que permitan iterar por separado sin pisarse. No contratar recursos, no cambiar rutas/DNS/servicios/OAuth/watchdog sin autorización y revisión cruzada.

## A. Contrato de tres entornos

| Entorno | Fuente Git | Acceso HTTPS | Persistencia | Promoción |
| --- | --- | --- | --- | --- |
| **MAIN (beta canónica)** | commit exacto revisado de `main`, inmovilizado en manifiesto de despliegue | un único hostname estable, URL oficial de Companion | Owner DB, ledger, jobs, worker, artefactos de main | solo pipeline de release probado y aprobado; rollback reversible |
| **LAB JM** | revisión explícita de rama de Chema (incluido candidato multicanción cuando publicable) | hostname laboratorio JM independiente y claramente etiquetado | Owner DB, sesiones, ledger y workspace separados | PR seleccionadas hacia main tras tests y revisión |
| **LAB FER** | revisión explícita de rama Fernando | hostname laboratorio FER independiente y etiquetado | Owner DB, sesiones, ledger y workspace separados | PR seleccionadas hacia main tras tests y revisión |

**Un pipeline** significa misma base de aplicación y contratos del Engine/Mixer/Stage/Push/Show y protocolo Companion, con la misma forma de ejecutar releases. **No** significa compartir sesiones, cookies, OAuth redirect, broker sockets, ledgers, tablas de proyectos, rutas de temporales, procesos cgroup o directorios de estado. El procesamiento multimedia sigue principalmente local vía Companion, sin subir originales por defecto.

## B. Capa de entrada mínima recomendada

**Preferencia:** mantener Cloudflare existente, sin añadir Vercel ni más stacks. Un único punto de entrada público por entorno: `main`, `jm`, `fer`. Tres hostnames (si hay dominio controlado que permita DNS; si no, decidir hostnames gratuitos estables y límites antes de provisionar). Cloudflare Pages/Workers puede presentar portada; Cloudflare Tunnel/Worker envía API autenticada hacia el backend correspondiente. **Una sola instalación cloudflared puede servir múltiples hostname-ingress** si la configuración, cuenta y seguridad lo permiten; no necesariamente una VM, túnel o servicio cloudflared por entorno.

No elegir `workers.dev` o `sslip.io` como nombre definitivo sin comprobar OAuth exact-origin, protección y control de DNS/TLS. Hostnames de prueba históricos se inventarían y retiran solo tras verificar clientes, redirecciones y ausencia de usuarios.

**Backend:** pueden coexistir puertos loopback distintos sobre la misma VM para tres instancias, sujeto a CPU/RAM/almacenamiento/FFmpeg y la política de apagado. Ninguna instancia pública apunta a un portal o SQLite de otra. Los entornos experimentales no deben impedir que MAIN se recupere; límites por Owner y prioridad/colas si la capacidad no permite tres renders simultáneos.

## C. Fotografía verificada en VM antes del acuerdo

- `montara-main.service` activo en loopback `:8103`.
- `montara-owner-beta.service` activo en loopback `:8115`.
- `montara-owner-h4-native.service` activo en loopback `:8116`; H4 Worker URL pública `https://montara-owner-h4.memoriainvalida001.workers.dev/`, `/healthz` devuelve 200, **pero su broker dedicado `montara-h4-native-broker.service` estaba inactivo/deshabilitado** y su socket no existía; el portal HTTP 200 no prueba `ensure` ni render.
- `montara-i26-broker.service` activo pero **es otro Owner** con otra SQLite/ledger; NO sustituir ni cambiar sus bindings.
- `montara-h4-staging236-broker.service` y `montara-h4-staging236-portal.service` instalados e inactivos, asociados a laboratorio de macbookair; no arrancarlos sin acuerdo.
- Nginx en :80/:443, entradas `35-242-225-127.sslip.io` y `multisong.35-242-225-127.sslip.io`; este último staging no está desplegado según STATUS-JM; puertos :8126/:8127 previstos en Nginx (no se observaron oyentes activos en instantánea). 
- `montara-owner-tunnel.service` es una instalación cloudflared ya activa.
- `montara-idle.timer` activo, **no** coordinado todavía con I6c.
- `main` en GitHub no es necesariamente el mismo código/bundle que ejecuta cada servicio; obligatoria trazabilidad de deploy, no solo HEAD.

Este inventario no determina todavía cuál de `:8103`, `:8116` o una ruta Urano sirve la beta oficial; **decisión JM+FER**. No redireccionar usuarios por nombres ambiguos.

## D. Decisión y gates concretos que faltan

1. **Chema/JM y Fernando/FER:** acordar un único frontend/back-end canónico MAIN, HTTPS y protocolo OAuth, sin confundir Main con H4 ni un staging. Elegir propietario administrativo de Cloudflare y DNS, seguridad y plan de rollback.
2. **Infra:** tabla completa por entorno: hostname, ruta Worker/Tunnel/Nginx, origen/puerto, systemd owner portal, broker, SQLite, ledger, worker/engine/mixer pins, Companion channel, exact deployed Git SHA y responsable. Cada celda debe mostrar `confirmed`, `missing` o `planned`.
3. **Runtime:** una sola receta reproducible de despliegue: commit SHA `main`, bundle SHA y manifest; preflight de identidad Owner→broker→SQLite→cgroup, evitar 503 como falsa readiness; `ensure` focalizado + test sintético, rollback.
4. **Recovery:** reusar I6a/b/c y PR #236 sin sistemas paralelos; resolver caso de unidad transitoria `not-found` manteniendo fail-closed y sin SQL manual; arrancar portal solo después del broker correcto. No activar watchdog o scripts de shutdown separados sin gate integrado y prueba OS.
5. **Compartición del pipeline:** fijar contrato de versiones Engine/Mixer y Companion; diferencias lab JM multicanción (`0dfd083` local sin ref remoto reproducible) frente a main; trabajo FER solo cherry-pick/PR selectivos. Si tres entornos no pueden ejecutar la misma versión de Engine, documentar compatibilidad y no afirmar pipeline único hasta probarlo.
6. **Aceptación mínima:** MAIN: login Google→Projects→`ensure`→subida de proxy sintético→editor/salida aislada; LAB JM y LAB FER: misma preflight `ensure` sobre sus propios catálogos; dos sesiones aisladas y no acceso cruzado; siguiente poweroff/reboot normal restaura MAIN. Evitar repetir el E2E humano de vídeo completo salvo regresión diagnosticada.
7. **Retirada de legacy:** solo al concluir la promoción, redactar inventario de accesos a retirar; no apagar ni borrar silenciosamente nada y mantener un rollback documentado.
8. **No introducir costos:** mantener VM y autoapagado; evaluar Cloudflare Workers/Tunnel vs Nginx existente antes de nuevos servicios. Si se requiere dominio/certificado, proponer opciones de cero nuevos cargos, verificar límites actuales y solicitar autorización expresa para cualquier gasto.

## E. Roles y propuesta de orden rápido

- **JM:** proponer cuál es Main canónico y su staging real, confirmar fuentes publicables de multicanción, origen/dominio y las rutas actuales de Urano/Nginx.
- **FER:** aportar trazabilidad de H4/Windows y corrección del broker not-found, preparar desplegables aislados y tests.
- **Ambos:** aprobar el contrato de tres entornos y plan de promoción/rollback en issue #216 antes de cambios infra; conservar `main` como única fuente de verdad para el código de beta, **no confundir main Git con servidor ya desplegado**.
- Tras acuerdo: un cambio acotado por vez, validación `ensure` primero; volver después a ÓRBITA y multicanción de cada laboratorio.

**No se ha autorizado** instalar entornos, mover DNS/OAuth, reiniciar servicios ajenos ni cambiar permisos o datos. La presente propuesta es documento, no decisión en firme.

# MONTARA · Matriz de ejecución MAIN / LAB-JM / LAB-FER
Fecha: 2026-11-16 · Responsable documento: FER · Estado: inventario **read-only** y plan acordado conceptualmente, **sin promoción ni deploy**.

**Decisión de JM (issue #216, comentario 6930616711):** Cloudflare existente preferido, un solo `cloudflared` con tres entradas si se demuestra factible; JM coordina release MAIN y LAB-JM; FER coordina LAB-FER, Companion Windows y arreglo O1; infraestructura compartida y MAIN pasan por ACK cruzado y autorización humana explícita.

## 1. Verificación real de recursos

| Recurso | Evidencia leída | Conclusión / pendiente |
| --- | --- | --- |
| Cloudflare cuenta `memoriainvalida001` | una cuenta conectada, **0 zonas DNS propias**, Workers scripts `montara-owner` y `montara-owner-h4` | **No se pueden prometer tres subdominios de dominio propio** sin una zona; requerirá identificar hostnames gratuitos estables o un dominio que controle el equipo (sin contratar todavía) |
| Cloudflare Tunnel | `montara-owner-fg`, API status `healthy`, configuración remota indicada; una instancia cloudflared activa en VM | candidato para reutilizar; **config ingress no legible desde API en consulta**; antes de cambiar, lectura verificada del mapa real y compatibilidad Cloudflare/OAuth |
| MAIN en VM | `montara-main.service` activo/enabled, loopback `:8103`, `/home/montara-main/app` | servicio real, **no asignarlo a web MAIN sin demostrar portal/OAuth/broker/pines y SHA exactos** |
| FER owner legacy | `montara-owner-beta.service` activo/enabled, loopback `:8115` | instalación histórica; no renombrar como LAB-FER sin decisión de migración de datos |
| H4 Owner | `montara-owner-h4-native.service` activo/enabled, loopback `:8116`; Worker `montara-owner-h4.memoriainvalida001.workers.dev`, healthz 200 | candidato técnico para LAB-FER, **no listo para Engine**: broker correspondiente inactivo |
| H4 broker dedicado | `montara-h4-native-broker.service` inactive/disabled, DB/ledger H4 separados | **bloqueante de ensure**; ledger H4 observado `running:1` con unidad antigua not-found; candidate fix O1 probó 26/26 mock/SQLite, pendiente revisión JM y prueba OS controlada |
| I26 legacy | `montara-i26-broker.service` activo/enabled, ledger diferente | **NO** usar para H4, no limpiar huérfanos ni cambiar bind |
| JM staging236 | `montara-h4-staging236-portal/broker` inactive/static, directorio macbookair | **No intervenir sin Chema**; no reasignar automáticamente a MAIN |
| Nginx/Urano | nginx HTTPS activo, hostnames `35-242-225-127.sslip.io` y `multisong.35-242-225-127.sslip.io`, upstreams configurados :8126/:8127; puertos sin oyentes en la instantánea | JM confirmará roles, TLS/OAuth, manifest y estado actual. No sustituir Cloudflare/Nginx sin mapeo exacto |
| Autoapagado | `montara-idle.timer` activo; I6c opt-in no integrado en runtime | conservar; antes de promoción coordinar admisión con watchdog y disponibilidad honesta si VM apagada |

**No se ha consultado ni publicado secreto, cookie, credencial, token ni contenido privado de los proyectos.**

## 2. Objetivo acordado; valores todavía no confirmados

| Entorno definitivo | Versión | HTTPS origen | Web/portal | Broker y Owner DB | Owner operativo | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| MAIN | release inmutable seleccionada de `main` | **por decidir** (Cloudflare preferido) | **por mapear**; no asumir `:8103` | propios, NO datos de JM/FER | JM release + ACK FER | PLANNED |
| LAB-JM | rama/manifest JM identificable; candidato multicanción aún sin ref remoto acreditado | **por decidir** | instancia aislada a elegir JM | propios, no staging236 sin acuerdo | JM | PLANNED |
| LAB-FER | rama/manifest FER | **por decidir**; H4 worker existente es histórico, no oficial lab | H4 :8116 solo como candidato | H4 broker dedicado, ledger y Owner root; bloqueado hasta recuperación verificada | FER | PLANNED |

## 3. Único pipeline y criterios de preparación

`HTTPS hostname exacto → Owner OAuth/CSRF exact-origin → portal/API → broker del MISMO Owner root/ledger → worker Engine/Mixer fijados → export/descarga (preferentemente original local Companion)`.

Una URL sana no significa Engine listo. El gate debe verificar:
- identidad de instancia (nombre, SHA aplicado, submódulos Engine/Mixer, protocolo Companion y capacidad read-only);
- broker socket/peer root, misma DB Owner montada RO, ledger/cgroup coherente y condiciones de recuperación, sin copiar/limpiar SQLite;
- health/readiness que distinga frontend disponible, VM apagada y Engine listo;
- OAuth/cookies/callback de origen fijo; separación de proyectos, colas, media, cachés y recursos; sin wildcard CORS.

## 4. Ejecución mínima, sin nueva infraestructura paralela

**P0 — JM+FER**: verificar orígenes y configuración real Cloudflare (0 zonas DNS en cuenta conectada), inventario de servicios JM, rol actual Nginx y correspondencia con release. Decidir tres hostnames realmente controlables; aceptar que `workers.dev` puede exigir scripts específicos y `sslip.io` no equivale a zona propia. Nada de inventar DNS.

**P1 — FER propietario técnico, JM revisor**: PR **pequeña** con cambio O1 exclusivamente en `SystemdDirect.show` y `RestrictedTargetControl.stop_verified`, fijado a main actual, pruebas de unidad not-found y cgroup vivo + rollback. Revisar preflight #236. Probar solo systemd real en entorno controlado antes de habilitar broker H4 y tras confirmar sin jobs activos; nada de reescribir broker.

**P2 — JM+FER**: escoger LAB-FER o LAB-JM piloto que requiera menos cambios y no use datos de otro; publicar un único origen con backend inequívoco (Cloudflare preferido), manifest y gate `ensure`. Validación acotada. Luego replicar la MISMA receta para segundo lab.

**P3 — JM release, FER revisión**: promover MAIN desde SHA de main, con E2E proporcional Google→Projects→ensure→Stage/Companion→MP4/download, rollback y decisión humana antes de rutas/DNS/servicios compartidos. Mantener accesos legacy documentados hasta retirada autorizada.

**P4**: JM multicanción y FER ÓRBITA vuelven a trabajar por su cuenta. Las tres webs comparten pipeline lógico y protocolo, **no** bases, procesos ni versiones experimentales.

## 5. Control de cambios

- **Verde:** Git branch FER, test, documento, auditoría read-only.
- **Ámbar:** PR broker, main, configuración de entrada por entorno, cambios de contrato (review JM+FER en issue #216).
- **Rojo:** Cloudflare DNS/routes, OAuth, systemd compartido, reconfiguración de túneles y Nginx, data, costes (autorización humana explícita y rollback).

Acuerdo fuente: [issue #216, JM comentario 6930616711](https://github.com/amehcgracia-byte/Montara/issues/216#issuecomment-6930616711). Las discusiones arquitectónicas continúan en ese issue referenciando [propuesta JM 6930420356](https://github.com/amehcgracia-byte/Montara/issues/216#issuecomment-6930420356).

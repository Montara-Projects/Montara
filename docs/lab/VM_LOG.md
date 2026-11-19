# Montara — registro de administración de la VM compartida

Este archivo registra intervenciones administrativas autorizadas y verificadas sobre la VM compartida. No incluye secretos, credenciales ni datos de usuarios. Los resultados corresponden al instante de cada comprobación y no sustituyen pruebas E2E.

| Fecha | Operador / autorización | Entorno | Acciones realizadas | Comprobación y reversión |
|---|---|---|---|---|
| 2026-11-19 | JM, aprobación Chema y Fernando en [PR #279](https://github.com/Montara-Projects/Montara/pull/279#issuecomment-7019200351) | Exclusivamente LAB-JM | Alta de usuarios del nuevo laboratorio: `montara-jmlab` (web, UID 987/GID 981) y `montara-jmlab-trusted` (cliente broker, UID 986); creación de `/var/lib/montara-h4-jmlab-owner` (0700), `/etc/montara-jmlab` (0700) y código root-owned bajo `/opt/montara/broker-h4-jmlab-native` mediante copia fiel de fuentes Python revisadas. | No se crearon usuarios ni cambios fuera del namespace JM. Para revertir, detener servicios JM y revisar antes de borrar datos; ningún borrado autorizado. |
| 2026-11-19 | JM, misma aprobación | Exclusivamente LAB-JM | Instalación y arranque de `montara-h4-jmlab-broker.service` (no habilitada al arranque automático); sockets `/run/montara-h4-jmlab-owner-admission/control.sock` y `/run/montara-h4-jmlab-broker/control.sock`; límites de lanzamiento previstos: 2 GiB RAM, 100 % CPU y 64 tareas por worker JM. | `systemctl show` ACTIVE/RUNNING; socket Owner root:montara-jmlab 0660; prueba `require_matching_broker` ejecutada como usuario web JM **PASS**. Detener únicamente `montara-h4-jmlab-broker.service` si se decide rollback. |
| 2026-11-19 | JM, misma aprobación | Exclusivamente LAB-JM | Instalación aislada de dependencias Python bajo `/opt/montara/jmlab-portal-runtime`; unidad `montara-h4-jmlab-portal.service` instalada y verificada para `127.0.0.1:8130`, usuario `montara-jmlab`, raíz privada; plantilla de configuración sin secretos. | Importación `urano.native_owner_trusted_wsgi` **PASS**; `systemd-analyze verify` **PASS**; portal **INACTIVE** por no disponer aún de credenciales OAuth exclusivas. No se ha publicado ningún Worker/VPC LAB-JM. |

## Límites y pasos pendientes

- **No modificados:** LAB-FER, MAIN, Owner legacy/H4, Work, sus Workers y VPC, DNS, sesiones, datos, recursos compartidos o trabajos activos. No se borraron ficheros de ningún laboratorio.
- **Pendiente:** configurar cliente Google OAuth propio de LAB-JM y URI de callback exacta, verificar credenciales privadas, arrancar portal, pruebas de autenticación/CSRF/propietario, después VPC Service exclusivo y Worker propio con E2E y rollback.
- **Fuente de coordinación:** [PR #279](https://github.com/Montara-Projects/Montara/pull/279#issuecomment-7019750587); [tablero privado](https://github.com/orgs/Montara-Projects/projects/1).
- Cualquier limpieza posterior de datos, usuarios o servicios exige autorización humana nueva y evidencia de propietario, respaldo, dependencias y reversión.

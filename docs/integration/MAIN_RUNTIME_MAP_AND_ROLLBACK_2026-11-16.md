# MAIN — mapa operativo verificable y reversión (auditoría 2026-11-16)

**Tipo:** inventario exclusivamente documental. **Estado:** parcialmente comprobado; ninguna promoción ni cambio de infraestructura autorizado.

**Fuente de coordinación:** [issue #216](https://github.com/amehcgracia-byte/Montara/issues/216), `docs/COLLABORATION.md`, informe JM de fase 3 (16-11-2026). Los hechos de la VM son una fotografía histórica, **no** un preflight actual. No incluir identidades privadas, secretos, rutas HOME ni cookies en este documento público.

## 1. No confundir `main` con el servicio MAIN

| Elemento | Hecho observado / límite de evidencia | Estado |
| --- | --- | --- |
| GitHub `main` | PR #246 integrada vía squash `42ee5edc8756f8ad880bb8e6328eec188ad54724` (16-11-2026). Consultar HEAD nuevamente antes de cada promoción. | Comprobado en GitHub en esa fecha |
| Engine pin de la rama | `92c7bc33f59baae92a8d61e5dd4bf0ce9685d79e` (último pin comunicado para `main`). | Informado; verificar manifest de HEAD actual |
| Mixer pin de la rama | `f15ff91c1b80fc5f157099dcd9451d958d553ae6`. | Informado; verificar manifest de HEAD actual |
| MAIN revisión Linux | Puerto interno `:8103`; servicio activo en última auditoría. Checkout asociado `641fec3`; **no prueba** del commit cargado por el proceso en memoria. | Puerto/checkout observados; binario servido sin verificar |
| MAIN autenticación | Instancia de revisión protegida mediante Basic Auth; **no** portal OAuth definitivo. | Observado en auditoría |
| URL pública canónica MAIN | **No elegida**. No convertir un hostname H4, Urano, sslip.io ni un Worker en MAIN por semejanza de nombres. | Pendiente |
| Ingress y TLS de MAIN | Cloudflare es la **opción preferida** en el acuerdo #216, pero no está verificado el mapping DNS/Worker/Tunnel → MAIN. Nginx puede formar parte del camino interno. | Pendiente |
| Procesos/dependencias | Comando ejecutable y cwd del proceso :8103, systemd unit vinculada, socket Owner, SQLite root, broker/ledger, Engine/Mixer efectivos, Companion esperado y claves de contrato. | Pendiente de lectura autorizada |
| Rollback operativo | Revisión instalada inmediatamente anterior, bundle firmado/identificado, configuración y ruta de origen precedente. | **No acreditado todavía** |
| LAB-JM y LAB-FER | :8101 (checkout `f05d6e9`) y :8102 (checkout `78e9e67`), respectivamente, observados como servidores Basic Auth de revisión; no asumir web OAuth. | No son MAIN canónica |
| H4 / legacy / Urano | H4 portal :8116 (broker H4 dedicado inactivo en la última lectura); legacy Owner :8115 con I26 distinto; rutas Urano :8126/:8127 sin listeners en esa instantánea. | Entornos separados; no usar como sustitutos |
| Multisong | Entrada HTTPS de staging prevista con backend :8128; candidato JM `0dfd083` presente como material local, no publicado como servicio en la última auditoría. | LAB candidato, NO release MAIN |

## 2. Verificación mínima read-only antes de designar MAIN

Realizar solo mediante acceso autorizado y **sin mostrar ni copiar secretos, token, correo, valores de variables de entorno, datos personales o paths privados**:

1. Confirmar estado de VM y puerto `:8103` con listados de sockets/procesos; no iniciar VM si está apagada sin autorización.
2. Relacionar PID → unidad systemd efectiva → ejecutable y checkout, revisando que el código cargado en memoria corresponda a un SHA reproducible. Un `git rev-parse HEAD` en el checkout **no basta** si el proceso fue arrancado antes o usa un paquete diferente.
3. Obtener versión de Engine/Mixer desde manifest del bundle **instalado y empleado por ese proceso**; no inferirla de la rama `main`.
4. Documentar upstream exacto de la ruta de entrada (Cloudflare Worker/Tunnel/Nginx) **sin leer ni publicar ficheros de credenciales**; validar exact-origin OAuth/CSRF antes de certificar URL.
5. Identificar datos persistentes y ledgers solo mediante nombres lógicos/IDs de entorno, sin publicar rutas privadas. Atestar qué broker corresponde a qué Owner y si está realmente listo para `ensure`; `healthz=200` no implica readiness.
6. Registrar revisión anterior, configuración de despliegue recuperable, capacidad disponible, estado de trabajos activos y dependencia de Companion. Si falta evidencia, mantener **PENDIENTE**.

**Ficha de release pendiente de rellenar con evidencia:**

| Campo | Valor |
| --- | --- |
| Fecha/hora de lectura VM | PENDIENTE |
| URL HTTPS canónica exacta | PENDIENTE |
| Cadena ingress pública → upstream → servicio | PENDIENTE |
| PID/unidad que sirve MAIN | PENDIENTE |
| SHA **efectivamente ejecutado** | PENDIENTE |
| Engine SHA efectivo / Mixer SHA efectivo | PENDIENTE / PENDIENTE |
| Owner + broker + ledger coherentes | PENDIENTE |
| Tipo de autenticación | Basic Auth observado; OAuth real pendiente |
| Companion/protocolo/orígenes permitidos | PENDIENTE |
| Release anterior y bundle para rollback | PENDIENTE |
| Checks `ensure`, login, export/descarga | PENDIENTE |

## 3. Procedimiento de reversión — diseño, **no ejecutar todavía**

**Gate previo a cambio de MAIN:** aprobación de JM para release, revisión cruzada de FER para contrato/infra compartida y autorización humana específica para cambios rojos (DNS, Worker/Tunnel, OAuth, systemd, datos, costes). Registrar antes y después en `docs/lab/VM_LOG.md` si hay cambios de administrador.

1. **Preparación:** capturar SHA/código y pines realmente servidos, configurar manifiesto de candidata y versión anterior, configuración de ingress existente, esquema y compatibilidad de SQLite, dependencias del Companion y ventana de tráfico/trabajos activos. Mantener originales y backups coherentes. Nunca registrar secretos.
2. **Prueba aislada:** nueva versión solo en entorno aprobado y aislado, comprobar exact-origin login/CSRF, identidad Owner↔broker↔SQLite/ledger, `ensure`, operación sintética acotada y descarga, sin originales de clientes ni renders largos innecesarios.
3. **Promoción:** cambiar únicamente la entrada MAIN tras aprobación, mantener ruta anterior accesible para reversión y conservar el bundle precedente; no reutilizar ni modificar I26/Staging236/H4 ni portales LAB.
4. **Rollback si falla:** detener nuevas admisiones hacia la candidata y volver **solo la ruta MAIN** al origen/version previo **comprobado**; no cortar workers vivos, no restaurar una SQLite antigua encima de trabajos nuevos, no editar reservas manualmente ni usar TTL para liberar huérfanos. Validar acceso, propiedad, proyectos y descarga en el origen restaurado.
5. **Salida:** publicar manifest de release, evidencias de pruebas, hora, hash y enlace al issue #216; retirar entrada antigua solo en una intervención separada tras verificar ausencia de consumidores.

**Condiciones de parada:** SHA efectivo desconocido; rutas ambiguas; broker/Owner o inode de DB no coinciden; OAuth/cookies incompatibles; no hay rollback probado; hay jobs activos sin drenaje; fallan login, proyectos propios, `ensure` o descarga.

## 4. Próximas acciones y responsables

- **JM:** completar lecturas autorizadas y la ficha del release real; mantener documento factual y coordinar la PR #236 independientemente.
- **FER:** revisar riesgos de broker/Cloudflare y continuar O1/H4 según #216; no modificar los servicios de JM.
- **Ambos + humanos:** acordar hostnames reales, preflight, promoción y rollback. No migrar, fusionar catálogos, limpiar datos o desplegar a partir de esta PR.

**Alcance de esta PR:** solo añade este documento. No ejecuta comandos VM, modifica configuración, cambia SHA de submódulos, servicios, datos, DNS, OAuth ni despliegue.

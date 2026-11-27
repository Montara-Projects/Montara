# STATUS — laboratorio Fernando (FER)
Actualizado: 2026-11-28. Responsable FER; coordinación Alfred-002.
- Protocolo #216: STATUS-FER (≤40 líneas), STATUS-JM independiente; acuerdos compartidos en [#415](https://github.com/Montara-Projects/Montara/issues/415). PR documental #419.
- **Hito de hoy: primer recorrido humano real de Montara Core V2, desde Google hasta descarga y reproducción del MP4.** V2 aislado de V1.
- ADR #415: monolito modular, identidad opaca, ports/adapters, SQLite mononodo, release declarativo. Cinco especialistas y auditoría arquitectónica inicial; FER/JM coordinan decisiones.
- [Montara-Core](https://github.com/Montara-Projects/Montara-Core), [MONTARA-BRAIN](https://github.com/Montara-Projects/MONTARA-BRAIN), [Project #2](https://github.com/orgs/Montara-Projects/projects/2): 30/32 encargos Done, #1 y #32 In Progress.
- H1/H2.1–H2.9: persistencia, autoridad Job/Task/Attempt, recetas, Engine existente, publicación verificada, OIDC, worker supervisado y recuperación; CI de paquete 100/100 previa.
- Core main verificado `d7c9a2abad1994166283267ac7292da6a7c1661b`, PR #15–20 integradas; [CI verde](https://github.com/Montara-Projects/Montara-Core/actions/runs/46076881258).
- H2.10: piloto privado persistente en Contabo, HTTPS Cloudflare y Google real operativos; dos identidades enroladas, otras dos pendientes. No reinstalación ni ampliación de gasto.
- Autonomía recuperada: SentinelX permite arranque único y estado del worker con privilegios mínimos, restricciones y revocación comprobadas; primer ciclo iniciado por Alfred sin terminal humano.
- QA humana FER: dos cuentas Google, creación y separación de proyectos incluso homónimos, recuperación del listado original tras cerrar sesión y volver a entrar. PASS de recorrido audiovisual y descarga de primera cuenta.
- MP4 sintético de 6 s, 1080p30 H264/AAC, 279812 B, SHA-256 idéntico a referencia H2.9, decode y oráculo 5/5 imagen + 3/3 audio según evidencia [BRAIN #32](https://github.com/Montara-Projects/MONTARA-BRAIN/issues/32). No extrapolar a concierto, edición comercial, Mac o 360.
- Pendientes acotados: comprobación directa de descarga cruzada y reapertura de resultado tras relogin humano; JM no disponible hoy. UI de ingeniería provisional: parpadeo de controles y detección de cambios de sesión entre pestañas.
- Supervisión: ciclo remoto completó render, systemctl RC0, lanzador RC1 por guarda de metadatos; causa probable documentada, corrección diferida a próximo mantenimiento autorizado, sin ocultar anomalía ni repetir render.
- **Siguiente:** validar con JM, cierre focalizado QA y auditoría independiente Work; luego H3 Companion Win/Mac, posteriormente paridad, rendimiento y portabilidad real. H2.10 sigue In Progress.
- Evolución de producto: login propio Google/email-password y derechos/cuotas backend; R2/pagos diferidos, sin precios decididos. Originales local-first/opt-in.
- V1: conservar PASS históricos Stage Windows/Mixer/Projects y LAB-JM, #392/#398 referencias de reproducibilidad. JM mantiene su línea; no se modificó runtime V1.
- Seguridad: no publicar secretos, identidades ni conectividad privada; sin gastos nuevos ni privilegios generales.

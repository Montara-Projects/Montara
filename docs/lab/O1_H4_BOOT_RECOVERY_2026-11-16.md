# O1 · H4 — Recuperación del servicio al reiniciar la VM (2026-11-16)

**Estado:** corrección operativa aplicada, respuesta HTTP pública comprobada. Falta comprobar el comportamiento en un **apagado/arranque real posterior** sin interferir con sesiones.

## Incidente observado

El botón **Abrir Montara** de Companion 0.6.10 abre la URL fija `https://montara-owner-h4.memoriainvalida001.workers.dev/`. El Worker Cloudflare respondía **HTTP 503** con `Private beta temporarily unavailable`.

El log del túnel reveló `connect: connection refused` al dirigirse a `127.0.0.1:8116`. No había oyente en ese puerto. Sí funcionaba el Owner **antiguo** del puerto 8115, **pero no es el destino H4** y no debe cambiarse la ruta para apuntarlo a 8115.

La unidad independiente `montara-owner-h4-native.service` existía, con puerto 8116 y el Engine del Companion `b867b3c72af8fe4685b487bcf1e09ffcc2a7c82b`. Su estado era `inactive` + `disabled` (no habilitada para arrancar con el usuario). El último paro registrado fue **2026-11-13 16:31 UTC**, con parada normal. Arranques posteriores de la VM no la iniciaron. `Restart=on-failure` estaba configurado, pero **no** soluciona una unidad `disabled` después del boot.

El túnel `montara-owner-tunnel.service` estaba activo y `enabled`, pero su `Wants/After` incluye `montara-owner-beta.service` (8115), no el H4 (8116). No es suficiente para iniciar H4 al boot. El gestor del usuario `fgardel00` tiene `Linger=yes`.

No encontramos procesos H4/FFmpeg huérfanos activos que explicaran el 503. Eso **no descarta** otras incidencias de limpieza de trabajos/SQLite; no se modificaron sus estados.

## Intervención realizada (autorizada)

1. Verificar que existen lanzador H4, aplicación nativa, Gunicorn y directorio privado; sin reemplazar ni actualizar código.
2. `systemctl --user start montara-owner-h4-native.service`: H4 comenzó a escuchar en **127.0.0.1:8116**, con master/worker Gunicorn activos y `NRestarts=0`.
3. Verificar `GET https://montara-owner-h4.memoriainvalida001.workers.dev/` → **HTTP 302** (entrada redirige a autenticación), `GET /healthz` → **HTTP 200**. La comprobación directa del backend por loopback sin contexto seguro da **403** y no equivale a salud pública.
4. `systemctl --user enable montara-owner-h4-native.service`: `default.target.wants` incluye H4. Tras habilitar, H4 figura **active + enabled**, `Linger=yes` y el túnel sigue habilitado. Nuevo `/healthz` público → **200**.
5. No se cambió Cloudflare, 8115, Engine, Mixer, tokens, código de Companion, servicios ajenos, ni VM de tamaño; no se reinició la VM.

## Responsabilidades y límites

- **GitHub** guarda código y este procedimiento, **no** arranca por sí solo los servicios de la VM.
- **Cloudflare Worker/Tunnel** encaminan solicitudes hacia el puerto privado **8116**; antes funcionaban pero fallaba el origen.
- **systemd --user** es responsable de iniciar y recuperar el H4 instalado en la VM. `enabled` + `Linger=yes` + `Restart=on-failure` protege contra el caso concreto.
- El código desplegado de H4 es un directorio candidato sin directorio `.git`; no hay SHA confirmado en el checkout de ejecución. La coincidencia de rutas y Engine no demuestra paridad exacta con el E2E humano. No se ha probado aún login Google humano, proyectos, rendimiento real ni recuperación de trabajos pendientes.
- La prueba anterior del **16/11** funcionó aunque el journal de esta unidad no muestra arranque posterior al 13/11. Puede haber existido otro proceso temporal: investigar si se busca trazabilidad completa, no atribuir sin evidencia.

## Validación pendiente

1. Usuario abre Montara desde Companion y comprueba Google login → Projects sin error 503.
2. En el **siguiente reinicio normal de la VM**, verificar `systemctl --user is-enabled montara-owner-h4-native.service` = `enabled`, `is-active` = `active`, `ss -ltn` muestra 8116 y `/healthz` público = 200 **antes** de la validación humana. No reiniciar la VM solo para este control durante la beta.
3. Si H4 no reanuda tras un boot futuro, analizar el journal de la unidad y el túnel con fecha, en lugar de cambiar el puerto o iniciar manualmente sin diagnóstico.
4. Por seguridad, no publicar la URL de OAuth junto con tokens ni registrar cabeceras/cookies en la documentación.

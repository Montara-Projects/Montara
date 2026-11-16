# I5b — E2E humano Stage Vídeo Windows y traspaso multiplataforma

Fecha: 2026-11-16. Estado: **Stage Vídeo E2E Windows completado en beta privada H4, con incidencias no bloqueantes**. Este documento registra observación humana; no equivale a aprobación de otros flujos, macOS ni instaladores para distribución pública.

> PARA CHEMA Y SU IA: el recorrido probado usa **Windows 10, Companion nativo .NET + servicio PyInstaller local y web H4**. No presupone que el Companion de macOS ni la web native de Chema funcionen sin adaptar configuración y comprobar contratos. **Ambos Companions son temporales**, convergen en un protocolo y no deben bifurcar productos.

## A. Evidencia humana E2E

1. Compilación Windows .NET 8, ventana y bandeja: PASS tras ajuste visual PR #241; quedan algunos textos extensos ligeramente truncados.
2. Servicio empaquetado `Montara.Companion.Service.exe` generado con Python 3.11 / PyInstaller, autoprueba `MONTARA_COMPANION_BUNDLE_SELFTEST_PASS`. Proceso que escucha en `127.0.0.1:47820`: `Montara.Companion.Service.exe` confirmado por PID/ExecutablePath (no terminal Python). Salud: `version=0.6.10`, `busy=false`, `ffmpeg=true`, `local_video.engine=b867b3c72af8fe4685b487bcf1e09ffcc2a7c82b`.
3. Recorrido browser: Google login → Stage vídeo → restore files → elegir carpeta local → elegir pista → sincronización → proxies pequeños → editor (~120 miniaturas) → render → download MP4: PASS funcional reportado por tester. El equipo local aumentó actividad durante render; VM mostró ~25 % CPU, **no** prueba del reparto de trabajo exacto: instrumentar.
4. El tester descargó MP4; comprobación explícita de reproducción final imagen/audio no consignada todavía. No marcar certificación de calidad de output.
5. **Incidencia abierta**: primer Edit desencadena recarga visible de ~120 miniaturas en vez de actualizar solo el plano editado. Investigar invalidación/versión de caché, sin modificar indiscriminadamente Engine. El historial de `main` ya incluye `c9c919d` (primera edición), `69bd9b7` (actualización selectiva), `12ec8fe` (continuidad sin recomputación), `7c728c6` (regresión), seguidos del pin `5d65ec3` a Engine `92c7bc33...`. Determinar si se solicita de nuevo por frontend, se regenera en Engine, o ambas cosas; fijar test con contador de solicitudes y caché antes/después de editar un único plano.
6. **UX abierta**: al render local conviene ofrecer `Abrir carpeta` / `Mostrar archivo` además de Download, con ruta local validada en Companion; no exponer rutas a otros orígenes ni dar acceso arbitrario al disco.

## B. Dependencias de despliegue que NO deben copiarse a ciegas

- Aplicación Windows: `companion/windows_native/Program.cs` tiene `BetaUrl = https://montara-owner-h4.memoriainvalida001.workers.dev/`. Es una URL de beta privada, no un requisito inherente de Companion.
- Servicio empaquetado Windows: `companion/windows_native/BundledService.cs` fija `MONTARA_COMPANION_ORIGINS` a dos hosts H4/Owner workers.dev y localhost. `companion/companion.py` aplica regex de origen para peticiones browser. Cambiar la web de entrada SIN actualizar y revisar la allowlist impide preflight/CORS o llamadas locales. Configurar **orígenes HTTPS concretos**; no aceptar `*`, orígenes arbitrarios ni reflejar `Origin` sin validación.
- `companion/windows_native/UpdateDiscovery.cs` confía el feed a H4. Esa ruta es separada de API de proyectos, render y autenticación. No reutilizar una URL de web no aprobada como fuente de instaladores.
- H4 actualmente usa Cloudflare Workers para entrada/Owner; no es una dependencia conceptual de Stage ni debe forzarse a Chema a usar Cloudflare. Distinguir dominio de interfaz, proxy/router HTTPS, Owner/auth, backend/VM y Companion localhost; documentar las rutas concretas y su responsable.
- URL comunicada por Chema: `https://35-242-225-127.sslip.io/urano/v1/native/`. Comprobación HTTP del 2026-11-16 desde VM: **502 Bad Gateway**, cabecera `nginx/1.24.0 (Ubuntu)`. Esto **no** permite inferir si detrás hay Vercel, GCP, contenedor o qué proceso está caído. Chema debe confirmar topología y backend upstream; no atribuirle proveedor.
- Google OAuth: verificar callback HTTPS exacto autorizado y dominio/sesión CSRF/cookies en la entrada propia, no copiar redirect URIs de H4. Nunca enviar cookies, client secrets, tokens o paths privados al handoff.
- Contrato entre web y Companion: verificar `/health`, `/projects`, reconocimiento de carpetas/ID, proxies, origin preflight, shot/save, trabajo ocupado, cancelación y render MP4; mantener originales localmente, permitir solo transferencias privadas/ligeras diseñadas, no fallback silencioso que suba originales.
- Mac: validar permisos del sistema para elegir carpetas, instalador/LaunchAgent, FFmpeg, Engine SHA, origen permitido, inicio/stop servicio, proyecto existente, proxies, render y destino final. **No** asumir que Windows QA certifica Mac.

## C. Criterio de aceptación independiente de hosting (Chema)

1. Acceso HTTPS y Google OAuth correcto con dominio elegido; preflight browser → Companion localhost acepta **solo** el origen autorizado; peticiones de un origen ajeno son rechazadas.
2. Browser no se queda `Pending` tras elegir carpeta; misma identidad de proyecto al reintentar, sin duplicar carpetas.
3. E2E macOS real con clips propios: restore/select/sync/proxy/edit/save/render/archivo local, misma versión/contrato Engine y sin subida del original.
4. Smoke test en Windows desde dominio de Chema **solo si** se acuerda y configura origen de QA por usuario; no degradar seguridad global para permitirlo.
5. Registro de tiempos/cargas por fase para las dos mejoras solicitadas por Chema (Listening to your videos, 13 pistas/proxies); medir A/B aislado con el mismo material.
6. UX de archivo final y primer Edit; verificar reproducción de MP4 con imagen y audio.
7. Distribución: identidades de firma persistentes y verificación del editor; Mac notarizado; canal HTTPS estable independiente de VM; actualización manual con consentimiento, jamás durante trabajo; rollback y proyectos intactos. Seguir `docs/integration/I5A_COMPANION_CROSS_PLATFORM_RELEASE_HANDOFF_2026-11-13.md`. Las firmas QA efímeras no son distribución.

## D. Orden de actuación

- **Ahora, antes de nuevos trabajos de optimización:** compartir este handoff y registrar E2E Windows con las dos incidencias. Es documentación, **no** cambio de código, no se redepliega Cloudflare, no se cambia main UI ni Companion Mac.
- **Siguiente rama rendimiento:** aislar el bug de miniaturas con test y fijación de las requests; medir las dos peticiones de Chema, después paralelismo/colas y otros cuellos.
- **Después:** profesionalizar releases, updater, Mac y UX de archivos, con validación propia por plataforma.

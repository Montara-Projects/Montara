# I5b — Ventana nativa útil para la beta Windows (2026-11-16)

## A. Novedad
- UI nativa Windows basada en la identidad visual oscura existente: estado dinámico cada 7 s en bandeja y panel, Engine SHA fijado de H4 comprobado (no basta con que aparezca `local_video`), FFmpeg, `busy` y versión real del servicio.
- Botones: iniciar el servicio **empaquetado** (sin pedir consola/Python); abrir solo la URL revisada de H4; buscar versiones de forma **solo lectura** (I5b); copiar diagnóstico mínimo sin tokens, rutas, nombres de archivos ni cookies.
- `Cerrar ventana` mantiene la bandeja y el worker; `Cerrar icono` no mata trabajos activos. No se añaden instalaciones ni permisos.
- Se elimina del panel cotidiano el botón de parche WinError5, que está obsoleto para el servicio que se empaqueta; `RenderPatch.cs` sigue disponible para QA no automática, sin borrados.

## B. Por qué ahora
- La validación humana Windows detectó `POST /projects Pending` y `WinError 10053` al responder desde SMART Beta por PowerShell. El nuevo cliente WinForms ejecuta el servicio PyInstaller con `CreateNoWindow=true`; **evita depender de la consola de PowerShell**, aunque el fallo de selector/repuesta aún requiere un E2E físico. La mejora de reintentos duplicados pertenece a la PR #237, independiente.
- La UI anterior mostraba «Motor detectado» con solo ver un objeto JSON y decía «sin subidas de vídeo» pese a que los proxies sí viajan a la VM. Ahora indica el estado real y «Proxies privados · Originales en tu equipo».

## C. Validación y límites
- Verificación obligatoria en GitHub Actions Windows: `dotnet build -warnaserror`, `--selftest-update`, PyInstaller y MSIX QA firmado solo para desarrollo.
- Este cambio **no** convierte la firma MSIX efímera en un instalador confiable. Falta una firma de editor válida, distribución aprobada y prueba física Windows 10 con el Companion existente. No invitar al usuario a importar certificados ni desactivar Defender.
- El lanzamiento local depende de `BundledService.Start()`; hay que ensayar conservación de `projects.json`, coexistencia con `0.6.10` y reacción ante Engine ocupado antes de sustituir la beta de escritorio.

## D. Siguiente foco
- Recoger CI de PR #237 y UI nativa.
- Con certificación y canal aprobado, probar I5b completo en Windows; confirmar `Continue → projects/new → draft → Save shot → MP4` sin duplicados ni `Pending`. No alterar H4/broker en mitad de sesión ni sustituir el `.pkg` Mac de Chema.

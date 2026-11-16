# O1 · ÓRBITA — Primera validación humana Windows (smoke de 10 segundos)

**Estado 2026-11-16:** script listo en rama, **no ejecutado todavía en Windows real**. 11 tests Python de esquema/agregación/privacidad pasan en VM; no sustituyen un test en Windows PowerShell 5.1.

## Qué se valida

Que el Companion instalado se detecta como `Montara.Companion.Service.exe` y puede medirse 10 segundos sin instalar Python, sin privilegios administrativos, sin modificar servicios y sin leer originales, tokens, rutas privadas ni archivos del usuario.

## Instrucciones

1. Abre Montara Companion como normalmente, asegurándote de que está activo en la bandeja de Windows.
2. Desde la rama `fernando/o1-orbita-20261116`, abre y descarga como archivo **Raw** `tools/o1/windows_companion_meter.ps1`, guardándolo con ese nombre en **Descargas**. Revisar el script completo antes de ejecutarlo. Nunca se recomienda un `curl | powershell` ni desactivar antivirus.
3. En PowerShell propio (sin Administrador), ejecutar:

```powershell
& "$env:USERPROFILE\Downloads\windows_companion_meter.ps1" -RunId o1-win-smoke-001 -DurationSeconds 10 -IntervalSeconds 2
```

4. Esperar resultado o mensaje de error. La salida se crea exclusivamente como archivo **nuevo** en `$env:TEMP\o1-companion-o1-win-smoke-001.json` y no sobrescribe si existe.
5. Informar de `PID`, `Samples`, CPU-s o del texto literal del error. Si aparece bloqueo de política de PowerShell, **detenerse y comunicarlo**; no modificar políticas ni intentar bypass.
6. El JSON contiene métricas de proceso y sello de tiempo, pero no información sobre originales ni secretos. No hace falta subirlo ni enviarlo para validar detección; si se necesita en una fase posterior, revisar contenido antes de compartir.

## Criterio de éxito

- Script ejecutado en Windows 10 real, sin elevación ni dependencias externas.
- Detecta **exactamente un** proceso servicio `Montara.Companion.Service.exe`; si hay cero o varios, falla sin crear informe.
- Registra 4–6 muestras o más (CIM puede tener latencia), CPU-s no negativa y RSS muestreado; escribe archivo JSON nuevo.
- No modifica Companion, no abre conexión de red y no necesita vídeos para la prueba de humo.

## Advertencias

- **No es benchmark real de Stage**, no verifica OAuth, Cloudflare, WAN ni reparto de trabajo.
- El reporte puede tener CPU-s 0 en reposo: normal.
- Si el ejecutable usa otro nombre en la instalación concreta, necesitamos observar el error y adaptar la detección; no adivinar procesos.
- En el siguiente ensayo completo, dos informes sobre el mismo `run_id` (Windows/VM) pasarán por `tests/o1_one_user_report.py`, y habrá que medir por separado tiempos de fases, tráfico HTTP y calidad del MP4.

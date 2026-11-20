# MONTARA · FER — Relevo operativo de limpieza y recuperación selectiva
**Fecha:** 20 noviembre 2026. **Propósito:** una IA sucesora debe continuar con acciones verificables, NO repetir auditorías generales ni reconstruir el Frankenstein de laboratorios.

## 0. Decisión expresa de Fernando
- En el proyecto solo trabajamos Fernando, Chema y sus IAs. Los directorios `fer` y `fgardel00` son ámbitos históricos propios de Fernando, **no dos clientes finales**. Los directorios `jm` y `macbookair` pertenecen al ámbito de Chema: **NO borrar, parar ni reconfigurar** sin su decisión.
- **Rescatar la mejor idea, evidencia y código diferencial; retirar lo demás.** Una mejora conceptual puede reimplementarse limpiamente sobre MAIN cuando portar código viejo complique el producto. No almacenar veinte versiones por nostalgia; tampoco romper regresiones o datos.
- Prioridad: primera limpieza propia, después lifecycle Engine y optimización híbrida. NO entrar todavía en licencias/certificados/instalador comercial.
- No tocar los clientes/URI Google OAuth (Montara Beta conserva 5–6 URI por esclarecer), ni staging236 de Chema, ni su media, ni sus servicios.
- Política de privacidad: originales locales salvo excepción técnica/consentimiento explícito; una subida completa MP3 sin Companion sigue registrada en #300.

## 1. Estado REAL comprobado (20/11/2026 16:48–16:53 UTC)
VM GCP ~96 GB, `df -h /` **74 GB usados, 23 GB libres, 77 %**. Medir de nuevo antes y después de cada tanda; datos variables por trabajo concurrente.

**Carpetas personales (bytes du -x -s -B1, GB decimales aprox.):**
- `/home/fer` 13.86 GB
- `/home/fgardel00` 10.34 GB
- `/home/jm` 6.68 GB (JM, NO tocar)
- `/home/macbookair` 5.01 GB (JM, NO tocar)
- `/home/montara-main` 2.21 GB (compartido)
Las dos carpetas históricas FER suman **~24.2 GB**, pero **no todo es basura**.

**Grandes directorios FER:**
- `/home/fer/lab-clips/originales` ~6.67 GB (ficheros reales de cámara/audio, algunos de varios GB): **proteger**, pueden servir para benchmark 360/long-media; investigar referencias/duplicación/portabilidad sin subir ni borrar originales.
- `/home/fer/montara-jupiter` ~2.21 GB, con `.venv` ~1.5 GB: candidato concreto para retirar **solo `.venv`** tras comprobar inexistencia de procesos/servicios, requisitos reproducibles y entorno alternativo; preservar documentación/experimentos.
- `/home/fer/montara` ~1.84 GB (medición anterior por carpeta /home/fer; una lectura posterior mostró ~561MB: no asumir consistencia temporal; reevaluar mount/enlaces antes de actuar).
- `/home/fer/.cache` ~1–2.1 GB según sesión; primero catalogar cachés regenerables, no borrar globalmente mientras corran procesos.
- `/home/fer/montara-data` ~0.60 GB: **datos/proyectos**, no borrado masivo.
- `/home/fgardel00/montara-owner-beta` ~0.70 GB en el último desglose (antes apareció 2GB por otras mediciones; verificar tamaño real): es **Git worktree base y su .git compartido**, NO eliminar.
- `/home/fgardel00/montara-personal-beta` ~2.1 GB, `montara-personal-beta-data` ~0.59 GB: inspeccionar antes de decidir; no confundir datos y código.
- `/home/fgardel00/urano-u13e2c-acceptance-20261108` ~0.97 GB tras retirar browser duplicado; `urano-u13e2d-20261108` ~0.63 GB; varias carpetas E2E/QA de 0.15–0.36 GB: candidatas **por copia**, validar pruebas, datos, procesos y worktrees.
- `/home/fgardel00/.cache` ~1.07 GB: identificar antes de limpiar.

**Espacio fuera de /home (NO atribuir automáticamente a Fernando):**
- `/var/lib/private` ~19.1 GB, MAIN H4 Owner ~11.69 GB (Uploads ~11GB; Sessions ~558MB), JM H4 Owner ~6.41 GB (Uploads ~6GB). Owner private es de servicio, puede contener proyectos activos: **NO borrar** sin enlazar SQLite/Owner/jobs y consentimiento; JM decide LAB-JM.
- `/opt/montara` ~12.35 GB; `/opt/montara/bundles` ~10.12 GB. Engine `9af275b` ~81MB MAIN activo; `b867b3c` ~153MB LAB-FER activo; `92c7bc3` ~1.4GB LAB-JM/BetaMAIN activos; `34c338d` ~1.4GB WORK inactivo; `b5e4831` ~1.4GB referencia antigua I26 pero NO ExecStart efectivo. Bundles gordos contienen `site/` ~1.3GB. **No eliminar hasta comprobar referencias efectivas, mounts, rollbacks y usuarios de servicios**.
- `/var/tmp/montara-caption-vocals.*` ~1.64GB propiedad `macbookair`, fechado 18/11: **pista a JM**, NO borrar. Otro temporal ~104MB `montara-beta-segment2-diagnostic`, root: investigar titular/uso.
- Root system `/usr`, `/var/lib/snapd`, etc: fuera de alcance del saneamiento FER.

## 2. Limpieza completada, NO repetir
- Se retiró **Chromium extraído ~410 MB** de `/home/fgardel00/urano-u13e2c-acceptance-20261108/browser`, sin referencias de proceso/systemd, conservando `outputs/` y `montara/`. Evidencia #54.
- Se retiraron **21 worktrees históricos I4–I28** de `/home/fgardel00/montara-integration-i*`. Antes de cada `git worktree remove --force`: comprobado HEAD ancestro de historia publicada `origin/fernando/integracion@4dfc68f`, sin referencia a esa ruta en systemd o scripts portal, sin cmdline de proceso coincidente. Cambios locales (staged/unstaged) a `changes.patch`, no rastreados a `untracked.tar.gz`, `head.txt`, `branch.txt`, `status.txt` y SHA256 comprobados en `/home/fgardel00/.local/share/montara-legacy-recovery/iN-20261120/`. Ramas/commits siguen en Git; **no destruir estos respaldos** antes de rescatar ideas útiles. 20 lotes iniciales ~3.55 GB de bajada medidos (actividad concurrente posible), I28 después ~179MB lógicos.
- PR #189, integración masiva histórica **CERRADA sin merge**, rama Git conservada. No volver a abrir/merge masivo. El MAIN actual conserva `SO_PEERCRED`, generaciones, ledger y `stop_verified`; I28 era workspace preliminar sin Stage real; MAIN Stage→Companion→MP4 **PASS humano** #265.
- El impacto de limpieza 85→81 % *previo* fue de causa no comprobada; no adjudicarlo a nuestros borrados. Último estado: 77 %.

## 3. Dependencia del portal beta antiguo: BLOQUEO legítimo
`montara-owner-beta.service` (127.0.0.1:8115) sigue activo y el script `start-owner-portal-smart.sh` fija `MONTARA_I27_OWNER_ENGINE_FLAG=private`. Su `owner_broker_preview.py` conecta `/run/montara-i27-admission/control.sock`, escuchado por **`montara-i26-broker.service`**; este también tiene `/run/montara-i26-broker/control.sock`.
El servicio se llama I26 pero su `systemctl show -p ExecStart` **efectivo** usa `engine-b867b3c` (por drop-in `30-smart-chema-stage.conf`), no `b5e4831`. **Nombres/grep de archivos .service antiguos NO equivalen a ejecución real**.
Cloudflare túnel `montara-owner-fg` está healthy pero API config devolvió `config:null`; logs históricos mencionan tráfico a 8115. **No se ha demostrado que el acceso beta OAuth ya no dependa del túnel/portal**, así que no detener éstos ni borrar sockets manualmente. No modificar URI OAuth, no tocar staging236. Próxima IA: trazar hostname→Worker→túnel→8115 vs MAIN/H4 con evidencia real sin leer/exponer secretos; sólo después ejecutar retirada reversible y observar. Los sockets `/run` son efímeros y casi no liberan disco.

## 4. Roadmap concreto: 4 bloques y condición de fin
**Bloque A — FER laboratorios/cachés (siguiente acción):**
1. Trabajar en unidades pequeñas, del mayor al menor. Validar tamaño en bytes, propósito, fecha, hash/ramas, referencia de systemd/procesos, ficheros no publicados, fixtures importantes, capacidad de reconstrucción y rollback.
2. **Rescatar solo** resumen de resultados y scripts/conceptos realmente únicos comparados con MAIN: `docs/lab/INVENTORY-FER.md` F1–F8, `docs/BENCHMARKS_HISTORICOS.md`, SATURNO 20–25, JÚPITER 17–19, LUNA y B01–B10. No confundir simulación con validación real. Registrar hipótesis/beneficio/limitaciones en #302 y crear PR pequeña solo si procede.
3. Primer candidato: virtualenv reproducible `/home/fer/montara-jupiter/.venv` ~1.5GB; retirar **si** se verifica sin referencias de ejecución, requisitos/lock y que no es único runtime esencial; registrar exacto antes/después y comprobar salud. **No tocar originales** `lab-clips/originales` mientras no se asegure un corpus para benchmarks.
4. Revisar laboratorios E2E/QA propios, cachés regenerables, `montara-personal-beta` sin borrar datos reales; conservar código compartido y respaldo de diferencias locales antes de eliminar worktrees.

**Bloque B — antiguo portal FER / I26 / bundles:** mapa de acceso beta y OAuth sin cambios, decidir retirarlo como conjunto si equivalente MAIN; pausa reversible de los servicios legacy en ventana controlada, pruebas de rutas y rollback, luego retirar instalaciones y bundles no usados. `b5e4831` y WORK `34c338d` son **candidatos, no autorizados como seguros**. Chema decide sus entornos.

**Bloque C — Owner Uploads/Main y JM:** inventario por Owner/proyecto/SQLite/jobs/retención, detectar subidas no referenciadas y repeticiones por hash; **no borrar** subidas MAIN/JM durante labores activas. Compartir con Chema pistas de `/home/jm`, `/home/macbookair` y `/var/tmp` sin intervenir.

**Bloque D — no volver a acumular:** corregir #271 Engine worker no liberado al New Project, crash/reboot/TTL y confirmación de cgroup; regla de retención 14 días solo cuando sea segura por estado Owner/SQLite; telemetría capacidad y presupuesto por laboratorio. Después retomamos planificador inteligente Companion/VM del #302, no otro Frankenstein.

## 5. Comprobaciones antes/después, límites y relevo
- Antes: `df -B1 /`, `du -x -s -B1 <ruta>`, `systemctl show <unidad> -p ExecStart -p ActiveState`, `ss -xlpn`, `git status --porcelain -uall`, buscar referencias **con permisos correctos**; no inferir que `grep` sin permiso encontró todo.
- Después: diferenciar GB lógicos de bytes realmente libres, comprobar MAIN/FER/JM y portal/túnel, no declarar E2E humano sin ejecutar; conservar reversión y documentar acción ejecutada, no solo propuesta.
- No pasar ni publicar tokens, email/OAuth secrets, rutas de originales sensibles, media, dumps de SQLite, vídeos privados o enlaces de acceso efímeros.
- Documentación canónica: issue #54 (limpieza); #271 (lifecycle Engine); #265 (E2E humano y benchmarks reales); #302 (roadmap de optimización); #300 (MP3 original subido); #216 coordinación; PR #189 cerrada. Owners: FER para sus labs, JM para los suyos, Joint para datos/infra compartidos.

**Criterio de cierre:** laboratorio sin ejecución ni mejora única verificada = desinstalar tras extraer resultados y salvaguardar cambios imprescindibles; servicio activo = demostrar sustituto y rollback; datos media = conservar hasta verificar referencia/consentimiento. No abrir más de una etapa de arqueología a la vez; priorizar liberar espacio y simplificar producto.

# H4 · Aceptación focalizada PR #246 + #236 (sin despliegue)
Fecha: 2026-11-16 · Responsable implementación FER, revisión JM, decisión de cambios compartidos JM+FER/humanos.

## Objetivo
Conectar el Owner H4 existente al **broker H4 dedicado**, usando los contratos preexistentes de #236 (identidad, socket, bind read-only y namespaces) y #246 (recuperación fail-closed de unidad transitoria ausente). No hay ninguna razón para tocar el broker I26/I27, reescribir el portal, cambiar Cloudflare, abrir puertos públicos o copiar bases de datos.

**ESTADO:** ejecución de producción **no autorizada**. Este documento es procedimiento de revisión y aceptación para un piloto aislado. No iniciar servicios H4/236, mover DNS, editar SQLite, habilitar watchdog ni tocar proyectos ajenos hasta ACK cruzado y autorización humana.

## Baseline observado (lectura real de la VM, 2026-11-16)
- `montara-owner-h4-native.service` usuario `fgardel00`, :8116, **active/enabled**. Tiene dependencia de red, no de broker systemd.
- `montara-h4-native-broker.service` systemd, `/opt/montara/broker-h4-native`, **inactive/disabled**. Usa `BindReadOnlyPaths=/home/fgardel00/montara-h4-owner-private:/run/montara-h4-owner-ro`, socket dedicado `/run/montara-h4-owner-admission/control.sock` **ausente**.
- `montara-i26-broker.service` y socket i27 activos, **catálogo y ledger diferentes**; dejarlos intactos.
- Staging236 `montara-h4-staging236-portal.service` y broker de macbookair inactivos, **no reutilizar ni arrancar**.
- `montara-idle.timer` activo; integración I6b/I6c todavía no habilitada en procesos de runtime.
- #246 HEAD `83e4ce9`, tests O1+I3/I6b/I6c 26/26 PASS; ensayo en systemd real `show` dos veces: `not-found/inactive/dead/MainPID=0/ControlGroup=`, exit 0, cgroup ausente.
- JM ha validado compatibilidad #236+#246 (46 tests/36 subtests PASS en checkout temporal); merge y activación son gates distintos.
- MAIN:8103, LAB-JM:8101, LAB-FER:8102 son servidores de revisión Basic Auth, **no** portales OAuth definitivos.

## Gate 0 — Antes de cualquier fusión (código solamente)
1. JM revisa la PR #246 `urano/private_broker_service.py`, `urano/restricted_systemd_broker.py`, `tests/test_o1_orphan_missing_unit.py`, y confirma ACK concreto de integración (o enmienda).
2. Registrar que CI `e2e (engine)` estaba rojo fuera del cambio, con evidencia de que no introduce regresión, y que los demás jobs relevantes pasaron. No declarar CI global verde.
3. Fusionar **solo #246** desde su rama basada en main si se aprueba, con HEAD esperado; ninguna otra rama O1.
4. JM actualiza/rebasa #236 sobre ese main y corre únicamente regresiones afectadas de namespaces H4 + recuperación O1. `engine/` y `mixer/` pines permanecen fijos.
5. Si un test o revisión detecta fallo, detener; no abrir nueva implementación en paralelo.

## Gate 1 — Aceptación de staging sin cambiar runtime
1. Elegir un Owner de staging **nuevo y aislado aprobado**, no el de macbookair ni el H4 productivo y sin copiar datos reales.
2. Fijar manifiesto: Git SHA, Engine pin, Mixer pin, bundle JM, expected protocol Companion, `MONTARA_H4_INSTANCE`, UID/GID, path Owner root, bind RO, socket, ledger, unidad, origen OAuth permitido y propietario.
3. Validar con el preflight #236 que el Owner ve exactamente el socket del broker dedicado; verificar par `st_dev/st_ino` del root y **montaje read-only** entre broker y portal; verificar permiso de socket 660 root:gid y parent 710, SO_PEERCRED root; fail closed ante falta de socket, mount no RO, SQLite incorrecta o identidad cruzada.
4. Ejecutar el check focalizado de #246 en ledger **temporal** de un Owner y unidad sintética desaparecida; intentar `ensure` solo contra la instancia staging elegida, sin medios originales; si falla, registrar status, componente, versión y causa.
5. No aceptar `/healthz=200` por sí solo; el gate es que admisión al broker correcto responda sin 503 y una transacción de prueba respete dueño/proyecto/cgroup.
6. Revertir la ruta de staging si falla (NO apuntar I26 al Owner H4); conservar SQLite de staging y no cortar jobs vivos.

## Gate 2 — Activación del H4 real (requiere permiso humano rojo explícito)
1. Confirmar quién usa el H4 actual, que no hay renders/jobs activos y que los datos y el ledger están respaldados **sin borrar filas**. Validar trabajos `running/orphaned` con generación y unidad exacta antes del primer start.
2. Preflight config `systemctl cat` y hash ejecutable contra manifest; actualizar binarios solo con deploy reversible y backup de configuración, **nunca parchear directo el servicio de JM ni I26**.
3. Acordar arranque **broker correcto → socket real + owner identity + ledger sano → preflight portal**. El portal es user service y broker es system service, así que una orden `After=` de una de las unidades **no** crea por sí sola una dependencia inter-manager; exigir un readiness gate efectivo o arranque controlado documentado.
4. Solo después de validar la identidad e identidad de proyecto, test `ensure` con una sesión real aprobada, Stage/import proxy sin originales, y parada limpia. Evitar nuevo E2E completo si contratos previos siguen fijos.
5. Reinicio/autostart de H4 y seguridad del watchdog son **otra decisión**; no habilitar `montara-h4-native-broker` ni cambiar `montara-idle` de manera automática en este piloto.

## Rollback (sin pérdida de datos)
- Si falla seguridad/readiness: retirar únicamente origen/ruta de piloto y detener solo procesos de piloto, **después de comprobar trabajos activos y drenaje**; no forzar stop sobre workers vivos.
- Restaurar versión anterior de bundle + configuración de piloto desde copia, sin modificar stores Owner o SQLite productivos.
- Mantener historial de logs (sin tokens), sha previo/nuevo, unit names y estado de jobs para diagnóstico; no borrar ni fusionar identidades.
- No existe un rollback automático seguro de una fusión Git que implique retroceder también el ledger si cambió de forma no compatible. Por ello no manipular estado real hasta demostrar compatibilidad sin migraciones.

## Entregable de validación humana (Fernando, Windows)
La acción humana se solicita **solo cuando los gates de servidor estén PASS**: abrir el origen LAB-FER acordado, Google OAuth, seleccionar proyecto de prueba, cargar medios derivados locales con Companion y pulsar Engine/Continue una vez. Recoger hora, URL, resultado, status de `/urano/v1/native/ensure` y estado visual sin cookies ni secretos. No subir originales ni hacer un render largo salvo fallo nuevo.

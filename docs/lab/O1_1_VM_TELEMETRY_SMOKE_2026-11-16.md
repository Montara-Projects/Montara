# O1.1 · ÓRBITA — instrumentación real y prueba de humo de VM

**Fecha:** 2026-11-16. **Estado:** instrumentos en rama O1 verificados; **NO** hay todavía benchmark E2E físico Windows↔VM con usuario interactuando.

## Implementación recuperada sin arrastrar ramas históricas

- `tests/o1_hybrid_node_meter.py`: recuperación selectiva del medidor U17B, con soporte de **1 usuario**. Mide solo un PID existente y descendientes mediante psutil; CPU-s como cota inferior, RSS muestreado, duración, muestras y fin de proceso. Sin comando, medios, archivos privados ni secretos en el informe. Opt-in, no daemon.
- `tests/o1_browser_transfer.py`: contador U17C de cabeceras/cuerpos HTTP observados por Playwright con orígenes explícitos. La suma de navegador **no** equivale a bytes WAN ni incluye transferencias ajenas al navegador. `original_upload_proven_absent=false`.
- `tests/o1_one_user_report.py`: reductor nuevo para una pareja **Companion Windows + servidor GCP** (y navegador opcional). Exige `run_id` coincidente, roles, dos etiquetas de host distintas, muestra válida y privacidad. No declara E2E, OAuth, ausencia de originales ni transferencia WAN por sí solo.
- `tests/test_o1_browser_transfer.py`, `tests/test_o1_one_user_report.py`: 9 contratos de validación; todos PASS en checkout aislado VM; `py_compile` PASS.

**Nota:** U17 histórico exigía dos clientes; no utilizar su agregador antiguo para falsificar baseline individual. El instrumento HTTP anterior etiquetaba topología CI compartida; O1 ahora la declara sin verificar hasta aportar evidencia física.

## Evidencia ejecutada en la VM (solo proceso H4 en reposo)

- Checkout QA aislado en espacio de usuario de integración; venv propio con `psutil 7.2.2`. No cambia servicio, componentes instalados ni `main`.
- Instrumento ejecutado sobre el PID maestro de Gunicorn del servicio H4 ya existente, durante 6 s a intervalos de 0,5 s.
- Resultado: **12 muestras**, **6,0 s**, **0,0 CPU-s** como cota inferior observada (en reposo), **67.137.536 bytes** de RSS máximo muestreado (aprox. 64 MiB), `root_exited_during_observation=false`.
- `network_measured=false`, `remote_server_verified=false`, transferencia de originales **desconocida**. Sin flujo de usuario ni FFmpeg en esta medición.
- Disco VM seguía mostrando `96G` total, `54G` utilizados y `43G` libres.
- **Esta prueba demuestra que el medidor funciona sobre un servidor real, no que Montara sea rápido ni que el reparto local/remoto esté medido.**

## Próximo gate: mismo trabajo, dos equipos físicos

1. Confirmar instancias, versiones del Companion/Engine y PID de cada proceso, además de código de H4; no confundir Engine local `b867b3c` con pin de `main` `92c7bc3`.
2. Utilizar el mismo `run_id` opaco, por ejemplo `o1-stage-cold-001`; etiquetar hosts `win-o1` y `gcp-o1`, sin usuario real/IP/ruta privada.
3. En paralelo, medir el proceso Companion Windows y el servicio H4 Gunicorn durante **el recorrido completo real** OAuth → proyecto → seleccionar archivos → proxy → transferir → Listening/sync → Edit → Save shot → render local → MP4 descargado/reproducido.
4. Para tráfico, enlazar el observador de Playwright a una **sesión instrumentada autorizada**; contabilizar aparte descargas directas y tráfico no visible a Playwright. No capturar tokens/cookies/URLs/cuerpos.
5. Registrar las marcas por fase desde el navegador y los dos procesos con inicio/final suficientemente sincronizados; no afirmar CPU-s por fase si solo se ha medido una ventana total.
6. Comparar una segunda ejecución de **mismo proyecto y medios** con caché reutilizada; no borrar caché de otros usuarios para simular frío.
7. Interpretar picos/tiempos con referencia a carga ajena, procesos compartidos, reintentos, CPU/RAM libre y calidad del MP4. No usar el resultado de reposo como línea base E2E.

### Ejemplo de instrumento pasivo (solo cuando se conozca el PID autorizado)

```bash
python tests/o1_hybrid_node_meter.py \
  --pid <PID_EXISTENTE> --role server --run-id o1-stage-cold-001 \
  --host-label gcp-o1 --scenario-clients 1 \
  --workload controlled-real --duration 120 --interval 0.5 \
  --output /ruta/privada/nueva/server-report.json
```

El informe de Companion se genera de forma equivalente sobre Windows con `--role client_companion` y su PID. La duración debe cubrir la fase a estudiar; el instrumento no espera ni arranca el trabajo del usuario.

### Combinación offline

```bash
PYTHONPATH=tests python tests/o1_one_user_report.py \
  --input /ruta/privada/nueva/server-report.json \
  --input /ruta/privada/nueva/companion-report.json \
  --output /ruta/privada/nueva/o1-one-user.json
```

No subir a GitHub informes con información privada sin revisar. No modificar Cloudflare, OAuth, FFMPEG, VM compartida, servicios, datos ni media originales para medir.

## Plan científico de optimización

Tras baseline completa, primera fase: solicitudes de Chema **Listening to your videos** y transferencia/preparación de pistas largas; identificar la operación exacta que cuesta tiempo/bytes/CPU. Elegir **una sola** hipótesis A/B de `Procesos y estudios de optimización híbrida`, FOCUS/SATURNO/JÚPITER o cachés existentes antes de modificar Engine/Companion. Coordinar con la IA de Chema por issue #216 cualquier contrato compartido.

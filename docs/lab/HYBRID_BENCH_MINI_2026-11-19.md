# MONTARA — benchmark híbrido mínimo y decisión (19/11/2026)

**Estado:** campaña corta cerrada en un worktree aislado; sin modificación de `main`, servicios, originales, Engine/Mixer, Companion ni Cloudflare. Base `main@9bd5a8d`. **No es E2E del producto**.

## Objetivo y fuentes

Comparar una fase **real y ya existente** (preparación de proxies + caché + resolución de receta desde original), **un solo candidato** (CRF 30 frente a 28 con todos los demás parámetros idénticos) y la capacidad de la misma VM al limitarla a 2 u 8 CPU. Utilizar los resultados para contrastar una **regla de asignación**, sin implementar ASDMR.

Fuentes: dos fixtures audiovisuales de laboratorio de 20 segundos, 1280×720, H.264/AAC, 25 fps, **no vídeos originales de Chema ni conciertos**; tamaños 4.308.978 y 4.304.518 bytes. Entorno: GCP Linux x86_64, ocho vCPU visibles, FFmpeg 6.1.1. Se utilizaron archivos temporales autolimpiados. El código actual `local_media/proxies.prepare` crea proxies H.264 CRF28/veryfast hasta 960 px de ancho, fps preservados y AAC96. Tres repeticiones por fixture para el camino de caché, mismas fuentes sin cambios.

## 1. Referencia real: proxy frío, caché y receta

| Muestra | Original (bytes) | Proxy actual (bytes) | Proxy/original | Preparación fría mediana | Caché caliente mediana |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cámara A | 4.308.978 | 946.091 | 21,96 % | 3,8215 s | 0,0010 s |
| Cámara B | 4.304.518 | 944.656 | 21,95 % | 3,8339 s | 0,0010 s |

Salida proxy con SHA-256 idéntico en tres corridas del **mismo** conjunto de recursos, 500 frames, 20s, 25fps y audio AAC. Preparación incluye FFmpeg, ffprobe y validación, mientras que caché caliente reutiliza y comprueba sin decodificar. No interpretar el ahorro de caché como mejora nueva: **MONTARA ya lo hace**. Un proxy puede crecer respecto al original con otros códecs/bitrate, así que estos dos fixtures no justifican una regla universal.

La resolución real `local_media.proxies.resolve_recipe` produjo segmentos ligados al **original inmutable**. Prueba FFmpeg posterior de dos cortes de 1s: **50 fotogramas, 2,000s, 0,3454s de ejecución**, salida 913.457 bytes. **No** fue el Editor/Cut/Edit/Export ni un MP4 de Stage por navegador.

## 2. A/B controlado: CRF28 actual frente a CRF30

Mismas entradas, escala 960×540, 25 fps, códec libx264 veryfast, audio AAC96, `copyts`, `start_at_zero`, `faststart`. Tres pares alternados en cámara A y par de corroboración en B; análisis completo de frames/duración y SSIM sobre el mismo original escalado.

| Métrica cámara A | CRF28 (control) | CRF30 (candidato) |
| --- | ---: | ---: |
| Tamaño mediano | 946.091 B | 782.157 B |
| Tiempo FFmpeg mediano | 3,6977s | 3,6374s |
| SSIM contra original | 0,972252 | 0,965706 |
| Corridas con mismo SHA dentro de variante | Sí | Sí |

Cámara B SSIM: 0,972251 (28) frente a 0,965628 (30). **−17,33 % bytes en A**, pero la fidelidad medible disminuye, y la diferencia de tiempo de codificación (~0,06s) es marginal y no prueba aceleración. **Decisión: no cambiar CRF productivo** sin revisión visual y material representativo (HDR/360/HEVC/conciertos). Un objetivo de menor tráfico no prevalece sobre calidad de preview.

## 3. Calibración de capacidad computacional

Mismo clip y misma configuración CRF28, usando **la MISMA VM**, `taskset -c 0,1` frente a `taskset -c 0-7`, tres corridas por configuración. No representa literalmente CPU, RAM ni SO de Windows/Mac.

| Métrica | 2 CPU disponibles | 8 CPU disponibles |
| --- | ---: | ---: |
| Tiempos de pared (s) | 6,388 / 6,430 / 6,4054 | 3,6241 / 3,6402 / 3,6453 |
| Mediana (s) | **6,4054** | **3,6402** |
| CPU total aprox. (s), tres muestras | 11,27 / 11,27 / 11,25 | 16,23 / 16,33 / 16,33 |
| RAM pico máxima proceso | 145.300 KiB | 221.896 KiB |
| SSIM frente a fuente | 0,972219 | 0,972252 |

La VM con ocho CPU recortó **≈43,2 %** del tiempo de pared respecto al mismo host limitado a dos; se incrementaron CPU-segundos y memoria pico. Ambos resultados preservaron 500 frames/20s/25fps/AAC, pero el SHA difirió entre límites de threads: la prueba inicial de comparación binaria falló en Phase 3, revelando una suposición inadecuada. Se separó Phase 3 en un segundo script y se validó equivalencia temporal y SSIM, no un SHA obligatorio entre afinidades. **No se reinició el costoso ensayo completo anterior**; sus Phase1/2 se habían completado correctamente.

## 4. Regla ASDMR / LUNA, solo simulación de decisión

Se tomó como **escenario**, NO como red medida hoy, el throughput agregado histórico ~3,72 Mbit/s de una carga anterior de Chema. Tiempo ideal de transferencia sin overhead: original A 4,31MB → **≥9,2666s**, proxy A 0,946MB → **≥2,0346s**.

| Ruta hipotética | Límite inferior, sin colas/descarga/reintentos |
| --- | ---: |
| Cómputo restringido 2 CPU, medio ya local | 6,4054s |
| VM 8 CPU, transferir original + procesar | 12,9068s |
| VM 8 CPU, transferir proxy + procesar | 5,6748s |

Aunque el tercer escenario parece ~0,73s más rápido, **NO prueba una ventaja de la VM**: no es una operación equivalente de calidad final si el original se queda local; faltan RTT, HTTPS/Cloudflare, cola, subida real, coste y verificación. Según la política de MONTARA, **render original de alta calidad permanece local** salvo aprobación explícita de otra ruta segura de transferencia. El proxy remoto puede servir para análisis/revisión cuando el contrato y la calidad lo permitan. No se midió ningún Windows/Mac ni WAN real; el subconjunto de CPU es solo una sensibilidad sobre GCP.

Regla conceptual mínima, sin software nuevo: escoger ejecutor solo si **tiene acceso permitido a fuentes suficientes**, el resultado garantiza la calidad requerida y `T_total=preparación+transferencia+cola+cómputo+descarga+verificación` favorece esa elección. Si falta medición, usar ruta validada. No implementar planificador dinámico ni inferir un beneficio de la literatura ASDMR sobre estos datos.

## Decisión y siguiente gate

1. **Conservar** caché/proxy actual y render desde original sin modificar.
2. **Archivar** CRF30 como alternativa condicionada a validación visual y material de uso real; no cambiar preset.
3. **No reabrir GOP**: SATURNO ya mostró ~−39,85 % de bytes selectivos en un fixture, pero ~0,30 % de mejora render, sin WAN real. La utilidad dependerá de un render remoto con medios originales selectivos autorizado, no de esta prueba.
4. **NO construir ASDMR todavía**: como máximo hoja de capacidades de Companion Windows/macOS y VM, y tiempos E2E reales.
5. **Esperar la A/A real de #267** con 13 stems en Mac de Chema y un E2E Stage→MP4 humano antes de atribuir aceleración global o cambiar distribución de tareas.

**Condición de cierre:** benchmark híbrido mínimo COMPLETADO en laboratorio; sin nuevas rondas ni arquitecturas hasta que exista un cuello real medido en el flujo compartido.

## Reproducibilidad y rigor

Scripts: `experiments/media_optimization/benchmark_hybrid_mini_20261119.py` (fases 1–4, ahora corregida la comparación entre afinidades) y `benchmark_hybrid_cpu_20261119.py` (fase CPU repetida sin exigir SHA bit-exact). Salida estructurada de CPU: `docs/lab/HYBRID_BENCH_MINI_CPU_2026-11-19.json`. Las cifras de fases 1–2 corresponden al stdout registrado durante la primera ejecución, que terminó con un AssertionError *después* de finalizar los resultados de fase 2; no hay JSON automático consolidado de esa primera pasada. Todo el material audiovisual temporal se eliminó al terminar. Sin PR, merge ni despliegue.

Referencias de contexto: `docs/integration/PROCESOS_Y_ESTUDIOS_DE_OPTIMIZACION_HIBRIDA_2026-11-12.md`, `docs/JUPITER_OPT_06_SATURNO_GOP_DECISION_2026-10-30.md`, `docs/BENCHMARK_PLAN_039.md`, GitHub #265 (campaña A/B) y #216 (coordinación).

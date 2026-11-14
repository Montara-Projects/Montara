# I7b — Separación visible de regresiones Engine y recorrido Montara (2026-11-14)

## A. Novedad
- El workflow E2E Linux conserva la misma batería de Engine fijado pero la ejecuta en un trabajo matricial propio `e2e (engine)`.
- `e2e (session)` ya no se corta al fallar ese bloque: puede ejecutar las pruebas posteriores de Mixer, navegación, proyectos privados, Stage, exportación y Companion.
- Los fallos Engine siguen siendo bloqueantes y visibles en GitHub Actions (no `continue-on-error`, ni `|| true`, ni exclusiones de tests).
- Stage, Push, Mix y contenedor privado se mantienen intactos; el trabajo `engine` no ejecuta recorrido de interfaz.

## B. Sin duplicidades
- El comando Engine es exactamente el que se ejecutaba dentro de Session; no se ha copiado ninguna prueba, modificado Engine/Mixer ni creado otro pipeline de producto.
- Incidencia previa de iluminación/encuadre/performance ya registrada en issue #221. Se separa la responsabilidad del fallo, no se da por resuelto.

## C. Validación
- Sintaxis YAML parseada y aserciones de cinco modos + condición estricta de ambos trabajos verificadas.
- Run previo #43624586851 en PR #232: Stage, Push, Mix y private-container PASS; `Montara regression tests` PASS; seis fallos de `engine/` en test_stage_performers, test_video_light y test_flat_framing.
- La aceptación E2E sigue pendiente hasta que tanto `e2e (session)` como `e2e (engine)` concluyan y se resuelvan sus fallos.

## D. Riesgos
- Un job nuevo ejecuta dependencias de Engine por separado, con mayor coste CI, pero evita ocultar pruebas posteriores.
- No resolver los seis fallos sin coordinación con Chema y sin probar sus causas; no forzar commit de submódulos.
- Nada desplegado en VM; no modificar usuarios, motores activos ni datos originales.

## E. Próximo paso
- Recoger los resultados completos de sesión y corregir únicamente fallos propios de la rama de integración. Coordinar issue #221 para Engine; I7b real con dos cuentas Google + Companion Win/Mac continúa pendiente.

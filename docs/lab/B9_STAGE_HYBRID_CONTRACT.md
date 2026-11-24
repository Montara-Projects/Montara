# B9 · Contrato experimental de sincronización híbrida Stage (FER)

Estado: **candidato aislado, NO integrado ni desplegado**. Basado en main 9bd5a8d (18/11/2026).

## Evidencia
Campañas B5–B8 en issue #265: prelocalizador con dos stems Opus en jam real de 14.248 s; guía de audio corta elegida sin offset histórico; refinamiento con funciones del Engine y verificación estable; negativos y cortos recuperados con la estrategia de referencia completa.

## Problema de contrato
`full-session.js::mixSessionForVideo` solicita `/montara/session/:id/video-source` **antes** de `/wizard/prepare`, y ese endpoint devuelve el `listen-all.webm` completo. El Engine emite `sync_map.json` con `master_duration_sec`, `offset_sec`, `offset_ranges` y el resultado de verificación. El Editor consume estos campos en `SyncSelection.review/windowCoverage` y `SessionVideo.excerptForClips`. Sustituir el WebM completo por una ventana breve SIN reconectar el reloj global rompería canciones, selección, export y soporte de varias cámaras.

## Lo implementado
`web/hybrid-stage-contract.js` es un módulo **puramente experimental, sin llamadas HTTP, temporizadores, modificación del DOM ni conexiones**. Proyecta offsets relativos de una ventana de guía al reloj global completo. Rechaza de modo fail-closed fuentes vacías, ventanas inválidas, offsets/rangos mal formados, falta de cobertura, `no_audio`, `low_confidence`, `unstable_sync`, errores y falta de verificación por tercios del Engine. Al proyectar `offset_ranges` suma T0 a **cada desplazamiento** sin colapsar los huecos. No fabrica IDs ni modifica el registro de cámara. Todas las cámaras de un lote deben pasar; si una falla el lote se rechaza para que el orquestador elija fallback sin aceptar parcialmente algo dudoso.

La salida **intencionadamente contiene `ready_for_stage:false`** y explica por qué: el navegador exige todavía un máster/guía real de la sesión y las canciones editables. Esto evita «hacer pasar» una guía corta por una fuente de cuatro horas y evita publicar offsets incompletos. Así obtenemos un primer gate reutilizable sin tocar la UX ni el Engine.

## Siguiente paso antes de habilitar Stage
1. Diseñar un endpoint backend Owner/autorizado de candidatos que devuelva `source_identity`, `guide_window`, `master_duration_sec`, `clip sync evidence`, `recipe_version` sin acceso arbitrario a ficheros de servidor, sin subir originales y con límites de CPU/cola. No exponer rutas absolutas ni confiar en el cliente para metadatos.
2. Adaptar el contrato de reproducción/editor para que la guía de escucha y la duración global de la sesión puedan representarse independientemente de la referencia corta usada para calcular Sync. Conservar canciones y límites en tiempo global, sin forzar la creación completa como condición previa del vídeo.
3. Aislar fallback real cuando confidence/estabilidad no sean suficientes, o el vídeo sea corto: carga de índice completo si está cacheado; si no, ruta Engine tradicional. Prohibido convertir un caso negativo en una elección arbitraria. No asumir que todos los vídeos correctos largos superan el gate disperso.
4. Test de `Wizard→Sync→Cut/Edit/Export` con medios reales, dos cámaras y rango musical; verificar tiempos/cachés y resultado MP4 reproducible. No certificar ahorro de 30% E2E antes de A/A real de Mac con #267.

Pruebas focalizadas: `node --test tests/hybrid-stage-contract.test.cjs tests/test_sync_selection.cjs`. No modifica submódulos `engine/`/`mixer/` ni el backend actual. Revisión cruzada ámbar por Chema antes de conectar al editor compartido.
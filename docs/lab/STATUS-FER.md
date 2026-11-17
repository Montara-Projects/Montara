# STATUS — laboratorio Fernando (FER)
Actualizado: 2026-11-17. Responsable FER. Fuente: GitHub + inspección SSH de nuestro entorno; no implica aceptación humana nueva.
- Gobierno: `docs/COLLABORATION.md`; coordinación IA por issue #216; no tocar STATUS-JM.
- Prioridad: Stage real → Companion Windows → MP4 verificable → benchmark E2E #265 → optimización híbrida; sin nuevos laboratorios.
- **Sync #255 / PR #266 FUSIONADA EN main**: squash `6953dcbd6add274a745e3f424c4fce3be2849801`. Cambio acotado a `web/montara.js`, `web/sync-selection.js` y test.
- Causa real #255: rango musical 97,913912–132,256273 s frente a vídeo sincronizado desde +207,121995 s; no había solapamiento. No atribuirlo a vídeo de ~20 s.
- Preflight #266: impide ausencia absoluta de cámara elegible antes de `/wizard/start`; intervalos discontinuos `offset_ranges` conforme a Engine. El invariante de cobertura Engine sigue vigente.
- QA #266: 22/22 tests Node PASS, sintaxis JS PASS en checkout temporal no servido. CI: Stage, Mix, Push, Session y privado PASS; Engine E2E FAIL #254 (iluminación/encuadre, fallo heredado). No declarar CI global verde.
- **LAB-FER Sync #266 DESPLEGADO 17-11 21:44 UTC:** portal `:8126` y broker FER ambos fijados a bundle inmutable `jm-ad7812a...` (PIDs verificados), Engine `b867b3c...` y Mixer `f15ff91...` intactos. Servicios activos, local `/healthz` 200, acceso público 302 OAuth; JM/Work sin cambios.
- **RC FER Sync activado en nuestro LAB:** editor `ad7812a` sobre 14cce: solo 2 JS + test, 22/22 PASS, 742 archivos iguales, manifiesto/overlay OK. Original anterior conservado; rollback privado `~/.local/share/montara/releases/fer-sync-255-backup-20261117T214441Z/restore.sh`. E2E humano posterior aún NO realizado.
- Despliegue de entorno exclusivo FER autorizado expresamente por Fernando; no requería aprobación adicional de Chema. La revisión cruzada #216 sigue vigente para contratos compartidos; no tocar Work/JM ni auth/transporte.
- E2E HUMANO previo 16-11: OAuth → proyecto/restauración → medios → Sync → editor/Save shot → render local Companion Windows → Download MP4. La reproducción y decodificación íntegra final no estaban acreditadas.
- Companion Windows habitual: `Montara.Companion.Service.exe` `127.0.0.1:47820`, protocolo 0.6.10, FFmpeg disponible. No cambiarlo ni aplicar auto-updater durante render; firma/rollback pendientes.
- Benchmark #265: primer caso de optimización real = jam Chema #34 de 13 pistas mono ~4 h; meta ≥30% menos tiempo hasta lista de canciones utilizable. Histórico 72:49 solo PUT→PUT, no E2E. Reutilizar proxy/caché/subida; faltan WAN, CPU/RAM Mac/VM y línea base A/A.
- **PR #267** observabilidad de la jam sin alterar pipeline: `fernando/first-usable-full-session-metrics-34`, 27/27 Node PASS; tiempos aceptado→previews, primer/último PUT confirmado, detección→lista editable. Revisión JM y validación en Mac real pendientes; sin merge/deploy ni cambio de originales.
- UX y producto: #252 primera edición/miniaturas aún necesita aceptación humana en LAB-FER; #251/#260 exportación a `Exports` pendiente Windows QA; multicanción/360 sin certificado E2E HTTPS.
- Seguridad: originales locales por defecto, sin uploads íntegros automáticos, sin cambios indiscriminados de Engine/Mixer o servicios ajenos; backup y rollback antes de despliegue dedicado.
- **Próximo gate FER = prueba humana Windows NOW:** Google→Stage mismo máster/vídeo→tramo sin cámara 1:38–2:12 debe avisar→tramo con cámara 3:40–4:10 debe continuar→Companion original local→MP4 reproducible y tiempos #265. No declarar E2E hasta terminarla.

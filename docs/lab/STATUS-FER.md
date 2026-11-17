# STATUS — laboratorio Fernando (FER)
Actualizado: 2026-11-17. Responsable FER. Fuente: GitHub + inspección SSH de nuestro entorno; no implica aceptación humana nueva.
- Gobierno: `docs/COLLABORATION.md`; coordinación IA por issue #216; no tocar STATUS-JM.
- Prioridad: Stage real → Companion Windows → MP4 verificable → benchmark E2E #265 → optimización híbrida; sin nuevos laboratorios.
- **Sync #255 / PR #266 FUSIONADA EN main**: squash `6953dcbd6add274a745e3f424c4fce3be2849801`. Cambio acotado a `web/montara.js`, `web/sync-selection.js` y test.
- Causa real #255: rango musical 97,913912–132,256273 s frente a vídeo sincronizado desde +207,121995 s; no había solapamiento. No atribuirlo a vídeo de ~20 s.
- Preflight #266: impide ausencia absoluta de cámara elegible antes de `/wizard/start`; intervalos discontinuos `offset_ranges` conforme a Engine. El invariante de cobertura Engine sigue vigente.
- QA #266: 22/22 tests Node PASS, sintaxis JS PASS en checkout temporal no servido. CI: Stage, Mix, Push, Session y privado PASS; Engine E2E FAIL #254 (iluminación/encuadre, fallo heredado). No declarar CI global verde.
- **LAB-FER aún NO desplegado con #266**: portal `:8126` y broker FER sirven bundle inmutable `jm-14cce126...`, Engine `b867b3c...`, Mixer `f15ff91...`. No cambiar servicios sin microvalidación, backup y rollback.
- **RC FER Sync listo SIN activar:** `fernando/h4-sync-255-release-candidate` HEAD `ad7812a` desde editor 14cce: solo 2 JS + test. 22/22 Node PASS, 742 archivos inalterados por SHA; manifiesto y módulo upload overlay previo verificados. No actualiza Engine/Mixer ni despliega `main` directamente; micro-revisión JM solicitada en #216/#255.
- Revisión cruzada solicitada a JM en PR #266 e issue #216; norma ámbar para Stage/contrato compartido. No tocar Work/JM/MAIN ni desplegar alteraciones de autenticación/transporte.
- E2E HUMANO previo 16-11: OAuth → proyecto/restauración → medios → Sync → editor/Save shot → render local Companion Windows → Download MP4. La reproducción y decodificación íntegra final no estaban acreditadas.
- Companion Windows habitual: `Montara.Companion.Service.exe` `127.0.0.1:47820`, protocolo 0.6.10, FFmpeg disponible. No cambiarlo ni aplicar auto-updater durante render; firma/rollback pendientes.
- Benchmark #265: primer caso de optimización real = jam Chema #34 de 13 pistas mono ~4 h; meta ≥30% menos tiempo hasta lista de canciones utilizable. Histórico 72:49 solo PUT→PUT, no E2E. Reutilizar proxy/caché/subida; faltan WAN, CPU/RAM Mac/VM y línea base A/A.
- **PR #267** instrumentación sin cambiar pipeline: `fernando/first-usable-full-session-metrics-34` HEAD `64e81dc`; tiempos de interacción, previews listas, detección→lista editable y cola de subida. 27/27 Node PASS; revisión JM/CI y validación con jam real Mac pendientes. Sin merge/deploy. Calidad/originales intactos.
- UX y producto: #252 primera edición/miniaturas aún necesita aceptación humana en LAB-FER; #251/#260 exportación a `Exports` pendiente Windows QA; multicanción/360 sin certificado E2E HTTPS.
- Seguridad: originales locales por defecto, sin uploads íntegros automáticos, sin cambios indiscriminados de Engine/Mixer o servicios ajenos; backup y rollback antes de despliegue dedicado.
- Próximo gate FER: revisar procedimiento bundle/editor + estado de trabajos propio antes de publicar #266 en portal privado; después ejecutar flujo real y registrar baseline #265.

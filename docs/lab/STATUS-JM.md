# STATUS — laboratorio Chema / JM
Actualizado: 2026-11-19. Corte documental: main GitHub `051c58130ad512aa05e841effc4f5651ca04a188`; NO acredita SHA/runtime desplegado.
- Norma: `AGENTS.md`, `CLAUDE.md`, `docs/COLLABORATION.md` y coordinación #216; JM edita SOLO STATUS-JM (≤40 líneas).

## Avance comprobado JM / FER
- **Engine #254 — JM DONE:** Chema aprobó zoom 14%; six paridades reconciliadas en Engine PR #76, commit `9af275b`; Linux `e2e(engine)` 226 PASS / 3 warnings (candidato, NO main).
- **Compatibilidad Engine #283 — JOINT pendiente FER:** su Companion usa pin `b867b3c`, JM base `92c7bc3`; revisión A–E y aceptación cruzada antes de merge #76/#282 o despliegue.
- **Exports #260 — JM DONE como entrega de código:** PR draft HEAD `1b7271d`, journal para caída Windows durante move, colisiones y recuperación; Mac 39 PASS + 1 prueba repetida tras materializar Engine, Node 7 PASS.
- **Exports Windows #275 — FER:** en su anterior HEAD hubo 11 PASS NTFS; nuevo `1b7271d` pendiente de Windows GUI Explorer, restart integral, disco desconectado, QA Stage→Companion→MP4. NO merge.
- **Métricas Full session #267 — revisión JM APPROVED:** HEAD FER `97bfab4`; JM node --check 3 JS + 10/10 Node tests PASS (9 métricas + batería U3C agrupada, 17 casos). SOLO medidas, sin cambios de códec, cupos, originales ni backend.
- **#267 todavía NO integrada:** CI global de ese HEAD incluye e2e(engine) rojo heredado #254; dos A/A reales Mac (13 pistas, caché/entorno comparable) y observación de lista editable PENDIENTES; no afirmar ganancia 30%.

## Beta JM / Music
- **Reels beta privada (18/11):** prueba Brave reportada PASS vídeo 30 s 1080×1920 H.264/AAC, descarga SHA coincidente y reproducción. Prueba visual Captions PASS; transcripción 'Read lyrics'/Whisper pendiente, NO afirmar subsanada.
- **Music → Full Session:** bug de WAV ORIGINAL ~285 MB rechazado por límite 256 MiB (HTTP 400) fue evitado al servir el JS proxy correcto, confirmación de Chema `Parche servido: true`; se observaron proxies Opus ~32–37 MiB. No confundir solución de ese 400 con E2E Music completo.
- **#278 OPEN:** carga real 15 pistas registró 5 HTTP 422 en Companion QA local y requirió reimportar 4; causa aún no acreditada. No incrementar FFmpeg ni automatizar reintentos sin raíz, contrato y FER.
- **Solicitud producto #278:** hasta 16 pistas, proxy audio ≤80.000.000 B/pista, originales WAV locales, hasta 30.000.000.000 B por vídeo ORIGINAL local (NO subida íntegra a VM), sin mínimo artificial para vídeos breves.
- **#278 BLOQUEADO para código/despliegue** por coordinación: primero revisión #267/FER F1, investigar 422 local y establecer plan de pruebas sin solapamiento con trabajo FER. Prueba E2E 4 h / 16 pistas pendiente.
- **#277 documental:** la propuesta previa de ZIP Music era LOCAL, nunca acreditar instalación/E2E por mera existencia del paquete. Evitar ruta, token, material privado o ID de usuario en Issues/CI.

## Otros gates / coordinación
- **#272 Owner autocierre:** FER draft `5a2be93` niega autocierre ante pestañas/RPC misma generación sin guardia atómica. Mantener cierre manual; sin merge/despliegue de autocierre hasta protocolo compartido seguro.
- **#252 primer Save shot:** tests Chromium Mac aislados de miniaturas positivos; E2E visual con LAB-JM servido/Windows FER sin acreditar. No borrar caches ajenas.
- **Work #264:** Companion HTTPS saliente sigue candidato draft, sin render+MP4 E2E por ese transporte ni firma/natividad integral acreditada. No confundir con Companion QA habitual.
- **LAB-JM Cloudflare:** draft en Project #1, pendiente acceso VPC Service (403 informado) y acuerdo MAIN/FER; no reutilizar túnel o binding ajeno ni crear despliegue incompleto.
- **VM compartida / OAuth / limpieza:** auditorías y tareas propias JM abiertas; cero revocaciones/borrados sin mapa, backup y autorización. FER limpia solo espacios propios.
- **Principio de madurez:** código de PR ≠ integrado a main ≠ servidor desplegado ≠ E2E humano; no cambiar Engine/Mixer pins, OAuth, autoapagado ni servicios ajenos sin gates.
- **Próximo JM:** revisar bloqueos #278 y aceptación Music, luego #277 documentación/QA y tareas propias de Cloudflare/OAuth; FER #275 Windows y #283 compatibilidad; registrar ACK en #216.

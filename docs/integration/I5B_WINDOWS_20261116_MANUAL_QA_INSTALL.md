# I5b Windows — puerta de prueba humana (QA privada)

## Alcance
1. El CI de `main` genera, si todo pasa, un artefacto privado de tres días: `montara-companion-msix-development`.
2. Debe contener un MSIX `0.6.12.0`, el **certificado público** de desarrollo `.cer`, `SHA256.txt` y `QA-MANIFEST.txt`.
3. `QA-MANIFEST.txt` contiene SHA exacto de commit, SHA-256 del MSIX, SHA-256 del certificado público y thumbprint. Los hashes se comprueban localmente antes de confiar o instalar. La clave privada es efímera y no se distribuye.
4. Paquete **solo de pruebas internas** de Fernando/Chema, no publicarlo a amigos todavía ni denominarlo versión final.

## Orden de prueba en el Windows de Fernando
1. Copiar antes un respaldo de `%LOCALAPPDATA%\MontaraSMARTBeta\projects.json` y `places.json`, si existen; no mover ni borrar originales/caché.
2. Cerrar voluntariamente la sesión antigua únicamente después de confirmar que no hay render ni transferencia en curso. La instalación no detiene nada por su cuenta.
3. Verificar los hashes, el certificado que firmó el MSIX y el origen privado del artefacto. Solo para esta prueba de desarrolladores, instalar explícitamente el certificado **público correcto** en `CurrentUser\TrustedPeople` (no `TrustedRoot`); no desactivar Defender/SmartScreen ni ampliar confianza a otros certificados.
4. Instalar el MSIX y abrir la interfaz. Confirmar bandeja, estado y botón iniciar servicio. Debe usar `127.0.0.1:47820` sin consola PowerShell. Si el instalador rechaza el certificado, **no forzar**; registrar mensaje.
5. Reutilizar archivos ya existentes de Stage; `Continue` debe dar `POST /projects=200`, después `wizard/projects/new` y `wizard/draft`. Si aparece `Pending`, registrar Timing/Response y detener pruebas repetitivas; no inventar otro proyecto.
6. Probar `Save shot` y exportación MP4 local, nunca aceptar subida de originales sin consentimiento.
7. Retirar la confianza del certificado de desarrollo tras finalizar su uso; el usuario puede conservar el paquete hasta una versión aprobada. Los renders, proyectos y originales no deben borrarse.

## Actualización a demanda
La búsqueda de nuevas versiones ya es solo lectura. **Actualizar** (descarga, firma de editor, progreso, rollback) sigue pendiente. MSIX autofirmados efímeros de ejecuciones diferentes no constituyen un canal de actualización sostenido. Requiere identidad de firma persistente para betas controladas o canal de distribución con firma reconocida.

## Límites de CI
El runner valida integridad del paquete y que el certificado público pertenece a la firma, pero no sustituye validación en Windows 10 real. No guardar certificados privados en artefactos y no añadir instaladores automáticos desde URL no verificada.

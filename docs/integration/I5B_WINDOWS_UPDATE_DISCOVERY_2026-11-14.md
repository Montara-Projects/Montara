# I5b — Bandeja Windows: comprobar versiones sin instalar (2026-11-14)

## A. Novedad
- En Windows, **Buscar actualizaciones** de bandeja y panel invocan la misma búsqueda asíncrona; ya no son botones ficticios.
- `UpdateDiscovery.cs` lee exclusivamente el catálogo JSON HTTPS, limita tamaño a 32 KiB, tiempo a 7 s, desactiva redirecciones y cookies, exige la ruta fija, compara semver/version de la bandeja y filtra Windows y CPU.
- El feed solo se inserta en el binario en el proceso de compilación mediante el metadato MSBuild `MontaraUpdateFeedUrl`, no vía usuario, navegador, fichero editable ni servicio Companion. Host permitido **únicamente el H4 beta actual**; cambiar de host requiere revisión de código, no un parámetro arbitrario.
- En los paquetes QA la propiedad está vacía, por lo que el botón explica que aún no existe un canal aprobado. No llama a la red.
- La consulta **nunca descarga, abre o ejecuta instaladores**, no detiene Companion y no cambia originales ni caché. Una versión anunciada no equivale a firma verificada.
- Autoprueba offline de validación de arquitectura, versión, catálogo/origen y origen arbitrario bloqueado, añadida al workflow Windows.

## B. Duplicidades evitadas
- Reutiliza `/montara/companion/releases` de I5a y el `Program.cs` de I5b. No hay segundo daemon/updater ni cambios en Companion macOS de Chema. No utiliza el ZIP/PowerShell retirado ni instala certificados.
- El protocolo localhost sigue en `127.0.0.1:47820`.

## C. Validación
- Validación definitiva de compilación WinForms, test de lógica `--selftest-update` y MSIX QA mediante `.github/workflows/companion-native-windows-ci.yml`. El runner Windows debe concluir en verde; compilar en Linux no acredita un MSIX.
- El catálogo beta H4 ahora mismo **no está publicado bajo la ruta exigida**. Incluso con URL configurada en una compilación firmada, hay que desplegar explícitamente ese endpoint para recibir versiones.
- `MontaraUpdateFeedUrl` nunca debe embebirse en paquetes QA o releases no aprobadas como si fueran firmadas.

## D. Puertas de seguridad
- Falta certificado de editor auténtico, verificación de cadena/timestamp, publicación firmada, clic de consentimiento, garantía de inactividad y rollback de paquetes. Por eso NO se implementa instalación.
- Los valores `signed=true`/hash de JSON no permiten confiar en un instalador ni reemplazan Get-AuthenticodeSignature. No sugerir desactivar SmartScreen.
- No cambia las instalaciones antiguas de Fernando ni el PKG/LaunchAgent de Chema.
- La preferencia futura es el mismo contrato para macOS y Windows, pero el menú Mac requiere revisión conjunta.

## E. Siguiente
- Publicar un catálogo firmado y comprobado en un origen estable, verificando antes identidad de editor; recién entonces activar feed en builds de distribución. Validación real Windows 10 y macOS con Companion y Engine ocupados/libres antes de permitir instalar.

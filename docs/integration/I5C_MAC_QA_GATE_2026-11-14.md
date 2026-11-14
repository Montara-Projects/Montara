# Mac Companion QA gate — 2026-11-14

## A. Novedad
- Workflow nuevo `.github/workflows/companion-macos-qa.yml` que ejecuta los tests de seguridad existentes y construye el `.pkg` en `macos-15` en PR y cambios de `main` relativos al instalador.
- Solo inspección de formato y expansión del paquete QA. No instala, firma, notariza, publica ni accede a secretos Apple.
- `contents: read`, sin artefactos de distribución ni token de escritura.

## B. Sin duplicación
- Reutiliza el **mismo** `companion/macos-installer/build.sh` y `tests/companion-native-installer.test.cjs` de Chema.
- No sustituye ni cambia su workflow de firma/notarización manual `macos-companion-package.yml`, su LaunchAgent, el editor ni el instalador Windows.

## C. Prueba obligatoria
- La compilación y tests en GitHub runner macOS deben terminar correctamente antes de fusionar. No se ha instalado el paquete en un Mac físico.
- Sin certificado Apple Developer ID Installer y notarización comprobada no debe publicarse un release.

## D. Riesgos
- Es una puerta de QA **no una release**. El código existente de publicación por credenciales deberá auditarse antes de crear un canal estable.
- Evitar subir originales, modificar instalaciones existentes o ejecutar un instalador durante un render; Windows y Mac siguen siendo implementaciones provisionales del mismo protocolo.

## E. Próximo paso
- Una vez fijado el origen de actualización y disponibles firmas aprobadas, unificar el manifiesto de distribución de I5a y validar Win10/macOS físicos. La beta H4 se mantiene separada de cualquier release pública.

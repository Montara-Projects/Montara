# STATUS — laboratorio Fernando
Actualizado: 2026-11-16 · Lo mantiene Fernando (máx. 40 líneas)
- Acuerdo IA compartido: docs/COLLABORATION.md, issue #216, AGENTS.md, CLAUDE.md.
- main HEAD verificado: 4bf32dc3a0f7b8d6ac43ad3a30bf7c70ce461d14.
- Pines main: Engine 92c7bc33f59baae92a8d61e5dd4bf0ce9685d79e, Mixer f15ff91c1b80fc5f157099dcd9451d958d553ae6.
- E2E HUMANO Stage Vídeo Windows 10 + H4: Google, proyecto/restore, carpeta, audio, sync, proxies, editor/Save shot, render local y Download MP4: PASS funcional 16-11.
- Companion nuevo empaquetado ejecutándose como Montara.Companion.Service.exe localhost:47820; health protocolo 0.6.10, FFmpeg OK, Engine b867b3c72af8fe4685b487bcf1e09ffcc2a7c82b (distinto del pin de main).
- E2E Windows H4 no acredita multicanción, Mac, Urano, Show/Push/Music ni despliegue Main; descarga verificada, última reproducción íntegra no documentada.
- PR fusionadas: #237 carpetas, #238 GUI Win, #239 CI regresión, #240 hashes/firma QA, #241 interfaz, #242 handoff E2E/hosting.
- Pendiente distribucion: firma persistente, updater manual seguro, rollback y validación MSIX para usuario final. Windows y Mac Companions actuales temporales.
- Abiertas: #236 preflight H4 staging; #243 primer Edit y ~120 miniaturas, diagnóstico/test sin fix runtime.
- Según informe Chema 13–16/11: multicanción local candidato 0dfd083, Stage 79902b0, portal e0b8cd6, Engine 34c338d, Mixer f15ff91. Dos canciones/render locales; no E2E HTTPS ni merge en main acreditados.
- VM comprobada 16-11 SSH: df -h / = 96G total, 54G usados, 43G libres (56%), discrepa del snapshot Chema 99%. Timer autoapagado activo.
- Entradas H4 Cloudflare y sslip.io Urano distintas; Google/Show de informe pueden ser históricos. Diagnóstico con URL, timestamp, HTTP y logs si se reproducen.
- Coordinación: verde autónomo; ámbar comunicación previa/cross-review contratos Engine/Mixer/Companion/Owner; rojo autorización humana (VM compartida, borrar, seguridad, coste).
- Plan P0 conciliar main y candidato multicanción; P1 preflight/disco/servicios; P2 staging E2E; P3 miniaturas y benchmarks Chema; P4 firmas/actualizaciones.
- Protección: no originales sin consentimiento; no mover/borrar datos ajenos; no gastos bancarios; no desactivar autoapagado.
- Detalle: docs/integration/I5B_STAGE_VIDEO_WINDOWS_E2E_CHEMA_HANDOFF_2026-11-16.md.

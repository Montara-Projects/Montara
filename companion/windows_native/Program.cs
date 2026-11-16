using System.Diagnostics;
using System.Drawing;
using System.Text.Json;
using System.Windows.Forms;

namespace Montara.Companion;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        if (Environment.GetCommandLineArgs().Contains("--selftest-update"))
        {
            Environment.ExitCode = UpdateDiscovery.SelfTest() ? 0 : 1;
            return;
        }
        ApplicationConfiguration.Initialize();
        Application.Run(new CompanionTray());
    }
}

internal sealed class CompanionTray : ApplicationContext
{
    private readonly NotifyIcon _tray;
    private readonly Icon _brandIcon;
    private readonly HttpClient _client = new() { Timeout = TimeSpan.FromSeconds(5) };
    private CompanionDashboard? _dashboard;
    private Process? _service;
    private readonly System.Windows.Forms.Timer _heartbeat = new() { Interval = 7000 };
    private bool _checking;
    private const string BetaUrl = "https://montara-owner-h4.memoriainvalida001.workers.dev/";
    internal const string PinnedEngine = "b867b3c72af8fe4685b487bcf1e09ffcc2a7c82b";

    internal CompanionTray()
    {
        _brandIcon = MontaraIcon.Create();
        var menu = new ContextMenuStrip();
        menu.Items.Add(new ToolStripMenuItem("Abrir Montara Companion", null,
            (_, _) => ShowDashboard()));
        menu.Items.Add(new ToolStripMenuItem("Iniciar servicio local", null,
            async (_, _) => await StartServiceAsync()));
        menu.Items.Add(new ToolStripMenuItem("Estado de conexión", null,
            async (_, _) => await ShowStatusAsync()));
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add(new ToolStripMenuItem("Buscar actualizaciones…", null,
            async (_, _) => await CheckUpdatesAsync()));
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add(new ToolStripMenuItem("Cerrar icono de Montara", null,
            (_, _) => ExitThread()));

        _tray = new NotifyIcon
        {
            Icon = _brandIcon,
            Text = "Montara Companion",
            Visible = true,
            ContextMenuStrip = menu
        };
        _tray.DoubleClick += (_, _) => ShowDashboard();
        _heartbeat.Tick += async (_, _) => await CheckLocalHealthAsync();
        _heartbeat.Start();

        // Open a proper branded window on first launch; the tray remains
        // available after the user closes it.
        ShowDashboard();
    }

    private void ShowDashboard()
    {
        if (_dashboard is not null && !_dashboard.IsDisposed)
        {
            _dashboard.Show();
            _dashboard.WindowState = FormWindowState.Normal;
            _dashboard.Activate();
            return;
        }

        _dashboard = new CompanionDashboard(_brandIcon,
            startService: StartServiceAsync,
            getStatus: ReadStatusAsync,
            openBeta: OpenBeta,
            checkUpdates: CheckUpdatesAsync);
        _dashboard.FormClosed += (_, _) => _dashboard = null;
        _dashboard.Show();
    }

    private static void OpenBeta()
    {
        // A fixed, reviewed beta URL. No browser-supplied URL or downloaded code.
        try
        {
            Process.Start(new ProcessStartInfo(BetaUrl) { UseShellExecute = true });
        }
        catch (System.ComponentModel.Win32Exception)
        {
            MessageBox.Show("No se pudo abrir el navegador. Introduce la URL de H4 manualmente.",
                "Montara Companion", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }

    private async Task CheckLocalHealthAsync()
    {
        if (_checking) return;
        _checking = true;
        try
        {
            var state = await ReadStatusAsync();
            if (_tray is not null)
                _tray.Text = state.Connected
                    ? state.Busy ? "Montara Companion · Render en curso"
                    : !state.EngineCompatible ? "Montara Companion · Engine incompatible"
                    : "Montara Companion · Conectado"
                    : "Montara Companion · Servicio desconectado";
            if (_dashboard is not null && !_dashboard.IsDisposed)
                _dashboard.DisplayStatus(state);
        }
        finally { _checking = false; }
    }

    private async Task<LocalStatus> ReadStatusAsync()
    {
        try
        {
            using var response = await _client.GetAsync(
                "http://127.0.0.1:47820/health",
                HttpCompletionOption.ResponseContentRead);
            if (!response.IsSuccessStatusCode) return LocalStatus.Disconnected;
            using var json = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            var payload = json.RootElement;
            if (!payload.TryGetProperty("app", out var app) ||
                app.GetString() != "montara-companion")
                return LocalStatus.Disconnected;

            string version = payload.TryGetProperty("version", out var v) &&
                v.ValueKind == JsonValueKind.String ? v.GetString() ?? "?" : "?";
            bool busy = payload.TryGetProperty("busy", out var b) &&
                b.ValueKind == JsonValueKind.True;
            bool ffmpeg = payload.TryGetProperty("ffmpeg", out var f) &&
                f.ValueKind == JsonValueKind.True;
            string engine = payload.TryGetProperty("local_video", out var e) &&
                e.ValueKind == JsonValueKind.Object &&
                e.TryGetProperty("engine", out var hash) &&
                hash.ValueKind == JsonValueKind.String
                    ? hash.GetString() ?? "" : "";
            bool compatible = string.Equals(engine, PinnedEngine, StringComparison.OrdinalIgnoreCase);
            return new LocalStatus(true, busy, ffmpeg, compatible, version, engine);
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or
                                   JsonException or IOException)
        {
            return LocalStatus.Disconnected;
        }
    }

    private async Task ShowStatusAsync()
    {
        var status = await ReadStatusAsync();
        MessageBox.Show(status.Connected
                ? $"Companion {status.Version} conectado.\n" +
                  (status.Busy ? "Trabajo activo: no actualizar.\n" : "Libre para trabajar.\n") +
                  (status.EngineCompatible ? "Engine H4 compatible." : "Engine H4 sin verificar o incompatible.")
                : "Companion no está conectado. Abre Montara para iniciar el servicio.",
            "Montara Companion", MessageBoxButtons.OK,
            status.Connected ? MessageBoxIcon.Information : MessageBoxIcon.Warning);
    }

    private async Task CheckUpdatesAsync()
    {
        var state = await ReadStatusAsync();
        var result = await UpdateDiscovery.CheckAsync(state.Busy);
        MessageBox.Show(result, "Montara · Actualizaciones",
            MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    private async Task StartServiceAsync()
    {
        var status = await ReadStatusAsync();
        if (status.Connected)
        {
            MessageBox.Show("Companion ya está en marcha. No se abrirá otra instancia.",
                "Montara Companion");
            return;
        }
        try
        {
            // Fully bundled service: never ask the user to select python.exe
            // or companion.py; no downloading or executing scripts.
            _service = BundledService.Start();
            await Task.Delay(550);
            if (_service.HasExited)
                throw new InvalidOperationException(
                    "El servicio local terminó al arrancar. Comprueba FFmpeg y el runtime de vídeo.");
        }
        catch (Exception ex) when (ex is FileNotFoundException or IOException or
                                   System.ComponentModel.Win32Exception or InvalidOperationException)
        {
            MessageBox.Show("No se pudo iniciar Companion: " + ex.Message,
                "Montara Companion", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        if (_dashboard is not null && !_dashboard.IsDisposed)
            await _dashboard.RefreshStatusAsync();
    }

    private async Task ApplyRenderFixAsync()
    {
        var status = await ReadStatusAsync();
        if (status.Connected)
        {
            MessageBox.Show("Cierra primero el servicio Companion. " +
                            "No se detendrán renders ni procesos automáticamente.",
                "Montara Companion", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        var result = RenderPatch.DescribeAndApply();
        MessageBox.Show(result, "Montara · Corrección de render",
            MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    protected override void ExitThreadCore()
    {
        // The local video service may have a job in progress: closing the tray
        // must never terminate it. Jobs and their files survive.
        if (_dashboard is not null && !_dashboard.IsDisposed) _dashboard.Close();
        _heartbeat.Stop();
        _heartbeat.Dispose();
        _tray.Visible = false;
        _tray.Dispose();
        _brandIcon.Dispose();
        _client.Dispose();
        _service?.Dispose();
        base.ExitThreadCore();
    }
}

internal sealed record LocalStatus(
    bool Connected, bool Busy, bool Ffmpeg, bool EngineCompatible,
    string Version, string EngineSha)
{
    internal static readonly LocalStatus Disconnected = new(false, false, false, false, "", "");
}

internal sealed class CompanionDashboard : Form
{
    private static readonly Color Coal = Color.FromArgb(16, 16, 20);
    private static readonly Color Panel = Color.FromArgb(31, 31, 36);
    private static readonly Color Ivory = Color.FromArgb(245, 243, 239);
    private static readonly Color Muted = Color.FromArgb(169, 170, 177);
    private static readonly Color Coral = Color.FromArgb(255, 79, 46);
    private static readonly Color Green = Color.FromArgb(105, 214, 155);
    private static readonly Color Amber = Color.FromArgb(255, 191, 91);

    private readonly Func<Task> _start;
    private readonly Func<Task<LocalStatus>> _status;
    private readonly Action _openBeta;
    private readonly Func<Task> _updates;
    private readonly Label _statusLabel;
    private readonly Label _subLabel;
    private readonly Button _startButton;
    private readonly Button _copyButton;
    private LocalStatus _latest = LocalStatus.Disconnected;

    internal CompanionDashboard(Icon icon,
        Func<Task> startService,
        Func<Task<LocalStatus>> getStatus,
        Action openBeta,
        Func<Task> checkUpdates)
    {
        _start = startService;
        _status = getStatus;
        _openBeta = openBeta;
        _updates = checkUpdates;

        Text = "Montara Companion";
        Icon = icon;
        BackColor = Coal;
        ForeColor = Ivory;
        ClientSize = new Size(462, 485);
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        Font = new Font("Segoe UI", 10f);
        AutoScaleMode = AutoScaleMode.Dpi;

        var logo = new PictureBox
        {
            Image = icon.ToBitmap(),
            SizeMode = PictureBoxSizeMode.Zoom,
            Location = new Point(24, 24),
            Size = new Size(55, 55),
            BackColor = Coal
        };
        Controls.Add(logo);
        Controls.Add(TextLabel("MONTARA", 90, 22, 322, 38,
            new Font("Segoe UI", 23f, FontStyle.Bold), Ivory));
        Controls.Add(TextLabel("COMPANION  ·  BETA WINDOWS", 94, 63, 325, 26,
            new Font("Segoe UI", 9f, FontStyle.Bold), Coral));

        var line = new Panel
        {
            Location = new Point(24, 104),
            Size = new Size(414, 1),
            BackColor = Color.FromArgb(56, 56, 63)
        };
        Controls.Add(line);

        var card = new Panel
        {
            Location = new Point(24, 125),
            Size = new Size(414, 120),
            BackColor = Panel
        };
        _statusLabel = TextLabel("Comprobando servicio…", 16, 17, 380, 35,
            new Font("Segoe UI", 14f, FontStyle.Bold), Ivory);
        _subLabel = TextLabel("Tus originales permanecen en este equipo.", 16, 57,
            390, 57, new Font("Segoe UI", 9f), Muted);
        card.Controls.Add(_statusLabel);
        card.Controls.Add(_subLabel);
        Controls.Add(card);

        _startButton = ActionButton("INICIAR COMPANION", 24, 263, 414, Coral, Coal);
        _startButton.Click += async (_, _) =>
        {
            _startButton.Enabled = false;
            try { await _start(); } finally
            {
                _startButton.Enabled = true;
                await RefreshStatusAsync();
            }
        };
        Controls.Add(_startButton);

        var launch = ActionButton("ABRIR MONTARA", 24, 316, 201, Panel, Ivory);
        launch.Click += (_, _) => _openBeta();
        Controls.Add(launch);

        var update = ActionButton("BUSCAR ACTUALIZACIONES", 237, 316, 201, Panel, Ivory);
        update.Click += async (_, _) =>
        {
            update.Enabled = false;
            try { await _updates(); }
            finally { if (!update.IsDisposed) update.Enabled = true; }
        };
        Controls.Add(update);

        _copyButton = ActionButton("COPIAR ESTADO PARA SOPORTE", 24, 369, 414, Panel, Ivory);
        _copyButton.Click += (_, _) =>
        {
            var summary = _latest.Connected
                ? $"Montara Companion {_latest.Version}; busy={_latest.Busy}; " +
                  $"ffmpeg={_latest.Ffmpeg}; engine_compatible={_latest.EngineCompatible}; " +
                  $"engine={_latest.EngineSha}"
                : "Montara Companion: servicio local desconectado";
            Clipboard.SetText(summary); // No cookies, tokens, filenames or private paths.
            MessageBox.Show("Estado técnico copiado sin datos privados.",
                "Montara Companion", MessageBoxButtons.OK, MessageBoxIcon.Information);
        };
        Controls.Add(_copyButton);

        Controls.Add(TextLabel("H4 · Proxies privados · Originales en tu equipo", 24, 427, 420, 24,
            new Font("Segoe UI", 9f), Muted));
        Controls.Add(TextLabel("Cerrar esta ventana no detiene los renders.", 24, 452, 420, 22,
            new Font("Segoe UI", 9f), Muted));

        Shown += async (_, _) => await RefreshStatusAsync();
    }

    internal async Task RefreshStatusAsync()
    {
        if (IsDisposed) return;
        var state = await _status();
        DisplayStatus(state);
    }

    internal void DisplayStatus(LocalStatus state)
    {
        if (IsDisposed) return;
        _latest = state;
        _statusLabel.Text = !state.Connected ? "○  Servicio desconectado"
            : state.Busy ? "●  Trabajo local en curso"
            : !state.EngineCompatible ? "●  Revisar versión del Engine"
            : !state.Ffmpeg ? "●  FFmpeg no disponible"
            : "●  Companion preparado";
        _statusLabel.ForeColor = !state.Connected ? Muted
            : state.Busy || !state.EngineCompatible || !state.Ffmpeg ? Amber : Green;
        _subLabel.Text = state.Connected
            ? $"Servicio {state.Version}  ·  FFmpeg {(state.Ffmpeg ? "OK" : "no detectado")}\n" +
              $"Engine H4 {(state.EngineCompatible ? "compatible" : "no verificado")}  ·  " +
              (state.Busy ? "Procesando: no actualizar" : "Listo para trabajar")
            : "Inicia el servicio local. No es necesario abrir PowerShell.";
        _startButton.Enabled = !state.Connected;
    }

    private static Label TextLabel(string text, int x, int y, int width, int height,
        Font font, Color color) => new()
        {
            Text = text,
            Location = new Point(x, y),
            Size = new Size(width, height),
            Font = font,
            ForeColor = color,
            AutoSize = false
        };

    private static Button ActionButton(string text, int x, int y, int width,
        Color background, Color foreground)
    {
        return new Button
        {
            Text = text,
            Location = new Point(x, y),
            Size = new Size(width, 42),
            Font = new Font("Segoe UI", 9f, FontStyle.Bold),
            BackColor = background,
            ForeColor = foreground,
            FlatStyle = FlatStyle.Flat,
            UseVisualStyleBackColor = false,
            Cursor = Cursors.Hand
        };
    }
}

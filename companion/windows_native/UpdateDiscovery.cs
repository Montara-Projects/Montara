using System.Net;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Montara.Companion;

/// <summary>
/// Read-only release discovery. Never downloads, launches, or trusts an installer.
/// The feed URL is embedded at signed-build time, not supplied by the browser,
/// environment, the local Companion service or a writable user file.
/// </summary>
internal static class UpdateDiscovery
{
    internal const string FeedMetadataKey = "MontaraCompanionUpdateFeed";
    private const int MaxCatalogBytes = 32768;

    internal static string? BuiltInFeed()
    {
        string? value = Assembly.GetExecutingAssembly()
            .GetCustomAttributes<AssemblyMetadataAttribute>()
            .FirstOrDefault(item => item.Key == FeedMetadataKey)?.Value;
        return string.IsNullOrWhiteSpace(value) ? null : value;
    }

    internal static bool TrustedFeed(string? url, out Uri? endpoint)
    {
        endpoint = null;
        if (string.IsNullOrWhiteSpace(url) || url.Length > 400 ||
            !Uri.TryCreate(url, UriKind.Absolute, out var parsed) ||
            parsed.Scheme != Uri.UriSchemeHttps ||
            !string.IsNullOrEmpty(parsed.UserInfo) ||
            parsed.Port != 443 ||
            !string.IsNullOrEmpty(parsed.Query) ||
            !string.IsNullOrEmpty(parsed.Fragment) ||
            parsed.AbsolutePath != "/montara/companion/releases" ||
            !string.Equals(parsed.Host, "montara-owner-h4.memoriainvalida001.workers.dev",
                           StringComparison.OrdinalIgnoreCase))
            return false;
        endpoint = parsed;
        return true;
    }

    internal static string ReadCatalog(string json, Version installed, Architecture architecture)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        if (root.ValueKind != JsonValueKind.Object ||
            !root.TryGetProperty("engine", out var engine) ||
            engine.ValueKind != JsonValueKind.String ||
            !Regex.IsMatch(engine.GetString() ?? "", "^[a-f0-9]{40}$") ||
            !root.TryGetProperty("releases", out var releases) ||
            releases.ValueKind != JsonValueKind.Array || releases.GetArrayLength() > 8)
            return "Catálogo no válido. No se ha descargado nada.";

        string arch = architecture switch
        {
            Architecture.X64 => "x64",
            Architecture.Arm64 => "arm64",
            _ => ""
        };
        if (arch == "")
            return "Esta arquitectura Windows no tiene canal de distribución.";

        Version? latest = null;
        foreach (var entry in releases.EnumerateArray())
        {
            if (entry.ValueKind != JsonValueKind.Object ||
                !entry.TryGetProperty("os", out var os) ||
                os.ValueKind != JsonValueKind.String || os.GetString() != "windows" ||
                !entry.TryGetProperty("arch", out var cpu) ||
                cpu.ValueKind != JsonValueKind.String || cpu.GetString() != arch ||
                !entry.TryGetProperty("version", out var value) ||
                value.ValueKind != JsonValueKind.String ||
                !Regex.IsMatch(value.GetString() ?? "", @"^[0-9]+(?:\.[0-9]+){2,3}$") ||
                !Version.TryParse(value.GetString(), out var version) ||
                version is null ||
                !entry.TryGetProperty("sha256", out var sha) ||
                sha.ValueKind != JsonValueKind.String ||
                !Regex.IsMatch(sha.GetString() ?? "", "^[a-f0-9]{64}$") ||
                !entry.TryGetProperty("download", out var download) ||
                download.ValueKind != JsonValueKind.String ||
                download.GetString() != $"/montara/companion/releases/download?os=windows&arch={arch}")
                continue;
            if (latest is null || version > latest)
                latest = version;
        }
        if (latest is null)
            return "No hay instaladores Windows aprobados en el catálogo.";
        if (latest <= installed)
            return $"Tu bandeja Montara ({installed}) está al día según el catálogo.";
        return $"Versión anunciada: {latest}. Tu bandeja: {installed}.\n\n" +
               "Hay una versión nueva en el catálogo, pero NO es una descarga " +
               "ni una comprobación de firma. La instalación está deshabilitada " +
               "hasta verificar el editor, la firma y que no haya trabajos activos.";
    }

    internal static async Task<string> CheckAsync(bool busy)
    {
        string? feed = BuiltInFeed();
        if (feed is null)
            return "Esta compilación de prueba todavía no tiene un canal " +
                   "de actualizaciones aprobado. No se descargará ningún instalador.";
        if (!TrustedFeed(feed, out var url) || url is null)
            return "Origen de actualizaciones inválido; consulta bloqueada.";

        try
        {
            using var handler = new HttpClientHandler
            {
                AllowAutoRedirect = false,
                UseCookies = false
            };
            using var client = new HttpClient(handler)
            {
                Timeout = TimeSpan.FromSeconds(7)
            };
            using var response = await client.GetAsync(
                url, HttpCompletionOption.ResponseHeadersRead);
            if (response.StatusCode != HttpStatusCode.OK ||
                response.Content.Headers.ContentLength > MaxCatalogBytes)
                return "El catálogo seguro no está disponible. No se ha descargado nada.";

            await using var stream = await response.Content.ReadAsStreamAsync();
            using var buffer = new MemoryStream();
            byte[] chunk = new byte[4096];
            int count;
            while ((count = await stream.ReadAsync(chunk)) != 0)
            {
                if (buffer.Length + count > MaxCatalogBytes)
                    return "Catálogo demasiado grande; se ha rechazado.";
                buffer.Write(chunk, 0, count);
            }
            string outcome = ReadCatalog(
                System.Text.Encoding.UTF8.GetString(buffer.ToArray()),
                Assembly.GetExecutingAssembly().GetName().Version ?? new Version(0, 0, 0, 0),
                RuntimeInformation.ProcessArchitecture);
            return busy ? outcome + "\n\nHay un trabajo local activo: no actualizar." : outcome;
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or
                                   IOException or JsonException or ArgumentException)
        {
            return "No se pudo consultar el catálogo. Ningún archivo se ha cambiado.";
        }
    }

    /// <summary>Offline build-gate self-test for the Windows CI runner.</summary>
    internal static bool SelfTest()
    {
        string sha = new('a', 64);
        string engine = new('b', 40);
        string release = $$"""
        {"engine":"{{engine}}","releases":[
          {"os":"windows","arch":"x64","version":"0.6.13.0",
           "sha256":"{{sha}}",
           "download":"/montara/companion/releases/download?os=windows&arch=x64"}]}
        """;
        Version current = new(0, 6, 12, 0);
        return ReadCatalog(release, current, Architecture.X64).Contains("0.6.13.0") &&
               ReadCatalog(release, new Version(0, 6, 14, 0), Architecture.X64).Contains("al día") &&
               ReadCatalog(release, current, Architecture.Arm64).Contains("No hay instaladores") &&
               ReadCatalog("""{"engine":"broken","releases":[]}""", current, Architecture.X64)
                   .Contains("no válido") &&
               !TrustedFeed("http://localhost:47820/montara/companion/releases", out _) &&
               !TrustedFeed("https://example.com/montara/companion/releases", out _) &&
               TrustedFeed("https://montara-owner-h4.memoriainvalida001.workers.dev/montara/companion/releases", out _);
    }
}

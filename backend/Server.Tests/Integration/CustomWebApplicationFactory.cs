using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;
using System.Net.Http.Json;
using System.Text.Json;
using System.Net;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;

namespace Server.Tests.Integration;

public class CustomWebApplicationFactory : WebApplicationFactory<Program>
{
    private readonly string _environment;
    private readonly bool _simulateLoopback;

    public CustomWebApplicationFactory() : this("Testing", false) { }

    internal CustomWebApplicationFactory(string environment, bool simulateLoopback)
    {
        _environment = environment;
        _simulateLoopback = simulateLoopback;
    }

    public string AuthDataDirectory { get; } = Path.Combine(Path.GetTempPath(), "hospital-rmf-auth-tests", Guid.NewGuid().ToString());

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment(_environment);
        if (_simulateLoopback)
        {
            builder.ConfigureServices(services =>
                services.AddSingleton<IStartupFilter, LoopbackStartupFilter>());
        }
        builder.ConfigureAppConfiguration((_, config) =>
        {
            config.AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["RosBridge:Url"] = "ws://127.0.0.1:1/unreachable-in-tests",
                ["Cors:Origins:0"] = "http://localhost:5173",
                ["Auth:DataDirectory"] = AuthDataDirectory,
            });
        });
    }

    public async Task<HttpClient> CreateSessionClientAsync()
    {
        var client = CreateClient(new WebApplicationFactoryClientOptions { BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false });
        await RefreshCsrfAsync(client);
        var response = await client.PostAsJsonAsync("/api/auth/register", new {
            name = "Test Operator", email = $"operator-{Guid.NewGuid():N}@example.test", password = "Testing-Passphrase-2026"
        });
        response.EnsureSuccessStatusCode();
        await RefreshCsrfAsync(client);
        return client;
    }

    public static async Task RefreshCsrfAsync(HttpClient client)
    {
        var body = await client.GetFromJsonAsync<JsonElement>("/api/auth/csrf");
        client.DefaultRequestHeaders.Remove("X-CSRF-TOKEN");
        client.DefaultRequestHeaders.Add("X-CSRF-TOKEN", body.GetProperty("token").GetString());
    }

    protected override void Dispose(bool disposing)
    {
        base.Dispose(disposing);
        if (disposing && Directory.Exists(AuthDataDirectory)) Directory.Delete(AuthDataDirectory, recursive: true);
    }

    private sealed class LoopbackStartupFilter : IStartupFilter
    {
        public Action<IApplicationBuilder> Configure(Action<IApplicationBuilder> next) => app =>
        {
            app.Use(async (context, nextMiddleware) =>
            {
                context.Connection.RemoteIpAddress = IPAddress.Loopback;
                await nextMiddleware();
            });
            next(app);
        };
    }
}

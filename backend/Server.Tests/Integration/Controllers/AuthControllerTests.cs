using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Server.Services.Auth;
using Xunit;

namespace Server.Tests.Integration.Controllers;

public class AuthControllerTests
{
    private const string Password = "Test-Passphrase-2026";

    private static HttpClient Client(CustomWebApplicationFactory factory) => factory.CreateClient(
        new WebApplicationFactoryClientOptions { BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false });

    [Fact]
    public async Task RegisterAcceptsSixDigitPasswordAndRejectsFiveDigits()
    {
        using var factory = new CustomWebApplicationFactory();
        using var client = Client(factory);
        await CustomWebApplicationFactory.RefreshCsrfAsync(client);
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync("/api/auth/register",
            new { name = "Nurse Judy", email = "judy@example.test", password = "12345" })).StatusCode);
        Assert.Equal(HttpStatusCode.Created, (await client.PostAsJsonAsync("/api/auth/register",
            new { name = "Nurse Judy", email = "judy@example.test", password = "123456" })).StatusCode);
        await CustomWebApplicationFactory.RefreshCsrfAsync(client);
        Assert.Equal(HttpStatusCode.NoContent, (await client.PostAsync("/api/auth/logout", null)).StatusCode);
        await CustomWebApplicationFactory.RefreshCsrfAsync(client);
        Assert.Equal(HttpStatusCode.OK, (await client.PostAsJsonAsync("/api/auth/login",
            new { email = "judy@example.test", password = "123456" })).StatusCode);
    }

    [Fact]
    public async Task RegisterPersistsHashedPasswordAndLogsInWithoutExposingCredentials()
    {
        using var factory = new CustomWebApplicationFactory();
        using var client = Client(factory);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/v1/task")).StatusCode);
        await CustomWebApplicationFactory.RefreshCsrfAsync(client);
        var response = await client.PostAsJsonAsync("/api/auth/register", new { name = "Nurse Judy", email = "Judy@example.test", password = Password });
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var body = await response.Content.ReadAsStringAsync();
        Assert.DoesNotContain("password", body, StringComparison.OrdinalIgnoreCase);
        Assert.Contains(response.Headers.GetValues("Set-Cookie"), value => value.Contains("HospitalRMF.Session") && value.Contains("httponly", StringComparison.OrdinalIgnoreCase));
        var profile = await client.GetFromJsonAsync<JsonElement>("/api/auth/me");
        Assert.Equal("judy@example.test", profile.GetProperty("email").GetString());
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/v1/task")).StatusCode);
        var stored = await File.ReadAllTextAsync(Path.Combine(factory.AuthDataDirectory, "accounts.json"));
        Assert.DoesNotContain(Password, stored);
        var reloaded = new AccountStore(factory.Services.GetRequiredService<IConfiguration>(), factory.Services.GetRequiredService<IWebHostEnvironment>());
        Assert.NotNull(await reloaded.ValidateAsync("JUDY@example.test", Password));
    }

    [Fact]
    public async Task LogoutClearsSessionAndCorrectCredentialsCanSignInAgain()
    {
        using var factory = new CustomWebApplicationFactory();
        using var client = Client(factory);
        await CustomWebApplicationFactory.RefreshCsrfAsync(client);
        Assert.Equal(HttpStatusCode.Created, (await client.PostAsJsonAsync("/api/auth/register", new { name = "Operator", email = "operator@example.test", password = Password })).StatusCode);
        await CustomWebApplicationFactory.RefreshCsrfAsync(client);
        Assert.Equal(HttpStatusCode.NoContent, (await client.PostAsync("/api/auth/logout", null)).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/auth/me")).StatusCode);
        await CustomWebApplicationFactory.RefreshCsrfAsync(client);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.PostAsJsonAsync("/api/auth/login", new { email = "operator@example.test", password = "Wrong password" })).StatusCode);
        var response = await client.PostAsJsonAsync("/api/auth/login", new { email = "OPERATOR@example.test", password = Password, rememberMe = true });
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Contains(response.Headers.GetValues("Set-Cookie"), value => value.Contains("HospitalRMF.Session") && value.Contains("expires=", StringComparison.OrdinalIgnoreCase));
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/auth/me")).StatusCode);
    }

    [Fact]
    public async Task DuplicateAccountsInvalidFieldsAndMissingCsrfAreRejected()
    {
        using var factory = new CustomWebApplicationFactory();
        using var client = Client(factory);
        var fields = new { name = "Operator", email = "operator@example.test", password = Password };
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync("/api/auth/register", fields)).StatusCode);
        await CustomWebApplicationFactory.RefreshCsrfAsync(client);
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync("/api/auth/register", new { name = "A", email = "invalid", password = "short" })).StatusCode);
        Assert.Equal(HttpStatusCode.Created, (await client.PostAsJsonAsync("/api/auth/register", fields)).StatusCode);
        await CustomWebApplicationFactory.RefreshCsrfAsync(client);
        Assert.Equal(HttpStatusCode.Conflict, (await client.PostAsJsonAsync("/api/auth/register", fields)).StatusCode);
        client.DefaultRequestHeaders.Remove("X-CSRF-TOKEN");
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync("/api/v1/task", new { })).StatusCode);
    }

    [Fact]
    public async Task ProfileUsesAuthenticatedAccountAndRejectsNonImageAvatars()
    {
        using var factory = new CustomWebApplicationFactory();
        using var client = await factory.CreateSessionClientAsync();
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PatchAsJsonAsync("/api/auth/profile", new { name = "Updated Name", avatarUrl = "javascript:alert(1)" })).StatusCode);
        var response = await client.PatchAsJsonAsync("/api/auth/profile", new { name = "Updated Name", avatarUrl = (string?)null });
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var profile = await client.GetFromJsonAsync<JsonElement>("/api/auth/me");
        Assert.Equal("Updated Name", profile.GetProperty("name").GetString());
    }

    [Fact]
    public async Task RepeatedSignInAttemptsAreRateLimited()
    {
        using var factory = new CustomWebApplicationFactory();
        using var client = Client(factory);
        await CustomWebApplicationFactory.RefreshCsrfAsync(client);
        for (var attempt = 0; attempt < 10; attempt++)
            Assert.Equal(HttpStatusCode.Unauthorized, (await client.PostAsJsonAsync("/api/auth/login", new {
                email = "unknown@example.test", password = Password
            })).StatusCode);
        Assert.Equal(HttpStatusCode.TooManyRequests, (await client.PostAsJsonAsync("/api/auth/login", new {
            email = "unknown@example.test", password = Password
        })).StatusCode);
    }

    [Fact]
    public async Task DevelopmentLoginCreatesLocalTestSessionOnlyInDevelopment()
    {
        using (var factory = new CustomWebApplicationFactory("Development", simulateLoopback: true))
        using (var client = Client(factory))
        {
            await CustomWebApplicationFactory.RefreshCsrfAsync(client);
            var response = await client.PostAsJsonAsync("/api/auth/dev-login", new { });
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            var profile = await response.Content.ReadFromJsonAsync<JsonElement>();
            Assert.Equal("developer@localhost.invalid", profile.GetProperty("email").GetString());
            Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/auth/me")).StatusCode);
        }

        using var testingFactory = new CustomWebApplicationFactory();
        using var testingClient = Client(testingFactory);
        await CustomWebApplicationFactory.RefreshCsrfAsync(testingClient);
        Assert.Equal(HttpStatusCode.NotFound,
            (await testingClient.PostAsJsonAsync("/api/auth/dev-login", new { })).StatusCode);
    }
}

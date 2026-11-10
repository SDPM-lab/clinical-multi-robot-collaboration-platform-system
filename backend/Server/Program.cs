using System.Text.Json;
using System.Text.Json.Serialization;
using Server.Services;
using Server.Services.Tasks;
using Server.Services.Auth;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Mvc;
using System.Threading.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews(options => options.Filters.Add(new AutoValidateAntiforgeryTokenAttribute()))
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.Converters.Add(new Server.Models.TaskTypeJsonConverter());
        options.JsonSerializerOptions.Converters.Add(
            new JsonStringEnumConverter<Server.Models.RobotCapability>(JsonNamingPolicy.SnakeCaseLower));
        options.JsonSerializerOptions.Converters.Add(
            new JsonStringEnumConverter(JsonNamingPolicy.CamelCase));
    });

// 帳號與 Cookie 簽章金鑰保存在本機；不將密碼或登入權杖放進前端儲存空間。
var accountDirectory = builder.Configuration["Auth:DataDirectory"] ?? Path.Combine(builder.Environment.ContentRootPath, "App_Data");
var keyDirectory = Directory.CreateDirectory(Path.Combine(accountDirectory, "keys"));
if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(keyDirectory.FullName, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
builder.Services.AddDataProtection().PersistKeysToFileSystem(keyDirectory).SetApplicationName("HospitalRMF");
builder.Services.AddSingleton<AccountStore>();
builder.Services.AddAntiforgery(options =>
{
    options.HeaderName = "X-CSRF-TOKEN";
    options.Cookie.Name = "HospitalRMF.Csrf";
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.Cookie.SecurePolicy = builder.Environment.IsDevelopment() ? CookieSecurePolicy.SameAsRequest : CookieSecurePolicy.Always;
});
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme).AddCookie(options =>
{
    options.Cookie.Name = "HospitalRMF.Session";
    options.Cookie.HttpOnly = true;
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.Cookie.SecurePolicy = builder.Environment.IsDevelopment() ? CookieSecurePolicy.SameAsRequest : CookieSecurePolicy.Always;
    options.SlidingExpiration = false;
    options.Events.OnRedirectToLogin = context => { context.Response.StatusCode = 401; return Task.CompletedTask; };
    options.Events.OnRedirectToAccessDenied = context => { context.Response.StatusCode = 403; return Task.CompletedTask; };
    options.Events.OnValidatePrincipal = async context =>
    {
        var id = context.Principal?.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
        if (id is null || await context.HttpContext.RequestServices.GetRequiredService<AccountStore>().FindByIdAsync(id) is null)
            context.RejectPrincipal();
    };
});
builder.Services.AddAuthorization(options => options.FallbackPolicy = new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build());
builder.Services.AddRateLimiter(options =>
{
    options.AddPolicy("auth", context => RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "unknown", _ => new FixedWindowRateLimiterOptions
        { PermitLimit = 10, Window = TimeSpan.FromMinutes(1), QueueLimit = 0, AutoReplenishment = true }));
    options.OnRejected = async (context, token) =>
    {
        context.HttpContext.Response.StatusCode = 429;
        await context.HttpContext.Response.WriteAsJsonAsync(new { code = "rate_limited" }, token);
    };
});

builder.Services.AddHttpClient();
builder.Services.AddSingleton<TaskStore>();
builder.Services.AddScoped<ITaskDispatcher, HttpTaskDispatcher>();
builder.Services.AddScoped<RosTaskStatusHandler>();
builder.Services.AddScoped<ITaskService, TaskService>();
builder.Services.AddHostedService<TaskScheduleWorker>();
builder.Services.AddSingleton<RobotStateStore>();
builder.Services.AddSingleton<RosBridgeTestService>();
builder.Services.AddHostedService(provider => provider.GetRequiredService<RosBridgeTestService>());

builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.WithOrigins(
                builder.Configuration.GetSection("Cors:Origins").Get<string[]>()
                ?? ["http://localhost:5173"])
            .AllowAnyHeader()
            .AllowAnyMethod();
        policy.AllowCredentials();
    });
});

var app = builder.Build();

app.UseExceptionHandler(handler => handler.Run(async context =>
{
    context.Response.StatusCode = 500;
    await context.Response.WriteAsJsonAsync(new { code = "server_error" });
}));

app.MapGet("/api.yml", (IWebHostEnvironment env) =>
{
    var path = Path.Combine(env.ContentRootPath, "..", "api.yml");
    return Results.Stream(File.OpenRead(path), "application/yaml");
}).AllowAnonymous();

if (app.Environment.IsDevelopment())
{
    app.UseSwaggerUI(options =>
    {
        options.SwaggerEndpoint("/api.yml", "人機協作平台 API v1.0");
    });
}

app.UseCors();
app.UseAuthentication();
app.UseAuthorization();
app.UseRateLimiter();
app.MapControllers(); //讓Controller 的 API 路由生效

app.Run(); //啟動 Web 伺服器並開始接收請求。

public partial class Program { }

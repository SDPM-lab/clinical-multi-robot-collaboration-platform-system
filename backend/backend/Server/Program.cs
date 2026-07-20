using System.Text.Json;
using System.Text.Json.Serialization;
using Server.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.Converters.Add(
            new JsonStringEnumConverter(JsonNamingPolicy.CamelCase));
    });

builder.Services.AddHttpClient();
builder.Services.AddScoped<ITaskService, TaskService>();
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
    });
});

var app = builder.Build();

app.MapGet("/api.yml", (IWebHostEnvironment env) =>
{
    var path = Path.Combine(env.ContentRootPath, "..", "api.yml");
    return Results.Stream(File.OpenRead(path), "application/yaml");
});

if (app.Environment.IsDevelopment())
{
    app.UseSwaggerUI(options =>
    {
        options.SwaggerEndpoint("/api.yml", "人機協作平台 API v1.0");
    });
}

app.UseCors();
app.MapControllers();

app.Run();

public partial class Program { }

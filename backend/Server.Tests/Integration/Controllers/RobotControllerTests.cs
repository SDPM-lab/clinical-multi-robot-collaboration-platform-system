using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using Server.Services;
using Server.Models;
using Xunit;

namespace Server.Tests.Integration.Controllers;

public class RobotControllerTests(CustomWebApplicationFactory factory) : IClassFixture<CustomWebApplicationFactory>
{
    [Fact]
    public async Task ApiReturnsSevenRegistrationsWithoutFabricatedTelemetry()
    {
        using var client = await factory.CreateSessionClientAsync();
        var result = await client.GetFromJsonAsync<JsonElement>("/api/robots");
        var robots = result.GetProperty("robots").EnumerateArray().ToArray();
        Assert.Equal(7,robots.Length);
        Assert.All(robots,robot=> { Assert.False(robot.GetProperty("hasTelemetry").GetBoolean()); Assert.Equal("L1",robot.GetProperty("levelName").GetString()); });
    }
}

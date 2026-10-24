using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Xunit;

namespace Server.Tests.Integration.Controllers;

public class TaskControllerTests(CustomWebApplicationFactory factory) : IClassFixture<CustomWebApplicationFactory>
{
    [Fact]
    public async Task CreateReadRescheduleDelete_UsesBackendTaskId()
    {
        using var client = factory.CreateClient();
        var scheduledAt = DateTimeOffset.UtcNow.AddDays(1);
        var response = await client.PostAsJsonAsync("/api/v1/task", new {
            taskType = "medicineDelivery", origin = "pharmacy", destination = "reception_back",
            priority = "normal", robotId = (string?)null, scheduledAt, note = "Test handoff"
        });
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var task = await response.Content.ReadFromJsonAsync<JsonElement>();
        var id = task.GetProperty("id").GetString();
        Assert.False(string.IsNullOrEmpty(id));
        Assert.Matches(@"^T\d{4,}$", task.GetProperty("taskCode").GetString()!);
        Assert.NotEqual(id, task.GetProperty("taskCode").GetString());
        Assert.Equal("pharmacy", task.GetProperty("source").GetString());
        Assert.Equal(JsonValueKind.Null, task.GetProperty("assignedRobot").ValueKind);
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync(response.Headers.Location)).StatusCode);
        Assert.Equal(HttpStatusCode.NoContent, (await client.PatchAsJsonAsync($"/api/v1/task/{id}/schedule", new { scheduledAt = scheduledAt.AddHours(1) })).StatusCode);
        Assert.Equal(HttpStatusCode.NoContent, (await client.DeleteAsync($"/api/v1/task/{id}")).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await client.GetAsync($"/api/v1/task/{id}")).StatusCode);
    }

    [Fact]
    public async Task MissingScheduledAt_ReturnsBadRequest()
    {
        using var client = factory.CreateClient();
        var response = await client.PostAsJsonAsync("/api/v1/task", new { taskType = "medicineDelivery", origin = "pharmacy", destination = "reception_back", priority = "normal" });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }
}

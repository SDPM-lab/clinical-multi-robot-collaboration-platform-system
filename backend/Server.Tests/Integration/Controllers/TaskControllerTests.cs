using Microsoft.Extensions.DependencyInjection;
using Server.Services;
using Server.Models;
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
        using var client = await factory.CreateSessionClientAsync();
        var scheduledAt = DateTimeOffset.UtcNow.AddDays(1);
        var response = await client.PostAsJsonAsync("/api/v1/task", new {
            taskType = "medication_delivery", source = "pharmacy", destination = "ward_a_2",
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
        var rescheduled = await client.PatchAsJsonAsync($"/api/v1/task/{id}/schedule", new { scheduledAt = scheduledAt.AddHours(1) });
        Assert.Equal(HttpStatusCode.Created, rescheduled.StatusCode);
        var replacement = await rescheduled.Content.ReadFromJsonAsync<JsonElement>();
        var previousId = id;
        id = replacement.GetProperty("id").GetString();
        Assert.NotEqual(previousId, id);
        Assert.Equal(HttpStatusCode.NotFound, (await client.GetAsync($"/api/v1/task/{previousId}")).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync(rescheduled.Headers.Location)).StatusCode);
        Assert.Equal(HttpStatusCode.NoContent, (await client.PatchAsJsonAsync($"/api/v1/task/{id}/priority", new { priority = "emergency" })).StatusCode);
        var updated = await client.GetFromJsonAsync<JsonElement>($"/api/v1/task/{id}");
        Assert.Equal("emergency", updated.GetProperty("priority").GetString());
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PatchAsJsonAsync($"/api/v1/task/{id}/priority", new { priority = 99 })).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PatchAsJsonAsync($"/api/v1/task/{id}/priority", new { })).StatusCode);
        Assert.Equal(HttpStatusCode.NoContent, (await client.DeleteAsync($"/api/v1/task/{id}")).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await client.GetAsync($"/api/v1/task/{id}")).StatusCode);
    }

    [Theory]
    [InlineData(RobotTaskStatus.Assigned)]
    [InlineData(RobotTaskStatus.Running)]
    public async Task AssignedAndRunningTasksCannotBeCancelledOrDeleted(RobotTaskStatus status)
    {
        using var client = await factory.CreateSessionClientAsync();
        using var scope = factory.Services.CreateScope();
        var tasks = scope.ServiceProvider.GetRequiredService<ITaskService>();
        var task = await tasks.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddDays(1) });
        await tasks.UpdateTaskStatusAsync(task.Id, status, robotId: "robot-a");
        Assert.Equal(HttpStatusCode.Conflict, (await client.PatchAsync($"/api/v1/task/{task.Id}/abort", null)).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await client.DeleteAsync($"/api/v1/task/{task.Id}")).StatusCode);
        Assert.Equal(status, task.Status);
        var response = await client.PatchAsJsonAsync($"/api/v1/task/{task.Id}/schedule", new { scheduledAt = DateTimeOffset.UtcNow.AddDays(2) });
        Assert.Equal(status == RobotTaskStatus.Assigned ? HttpStatusCode.Created : HttpStatusCode.Forbidden, response.StatusCode);
        if (status == RobotTaskStatus.Assigned)
        {
            var replacement = await response.Content.ReadFromJsonAsync<JsonElement>();
            Assert.NotEqual(task.Id, replacement.GetProperty("id").GetString());
            Assert.Equal("pending", replacement.GetProperty("status").GetString());
            Assert.Equal(JsonValueKind.Null, replacement.GetProperty("assignedRobot").ValueKind);
        }
    }

    [Fact]
    public async Task QueriesExposeAssignedRobotBeforeStartAndActualTimesForHistory()
    {
        using var client = await factory.CreateSessionClientAsync();
        using var scope = factory.Services.CreateScope();
        var tasks = scope.ServiceProvider.GetRequiredService<ITaskService>();
        var task = await tasks.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddDays(1) });
        await tasks.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Assigned, robotId: "R17");
        var assigned = await client.GetFromJsonAsync<JsonElement>($"/api/v1/task/{task.Id}");
        Assert.Equal("assigned", assigned.GetProperty("status").GetString());
        Assert.Equal("R17", assigned.GetProperty("assignedRobot").GetString());
        Assert.Equal(JsonValueKind.Null, assigned.GetProperty("startedAt").ValueKind);
        var start = DateTimeOffset.UtcNow.AddMinutes(-5);
        var finish = start.AddMinutes(3);
        await tasks.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Running, startedAt: start);
        await tasks.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Completed, finishedAt: finish);
        var records = await client.GetFromJsonAsync<JsonElement>("/api/v1/task");
        var record = Assert.Single(records.EnumerateArray(), entry => entry.GetProperty("id").GetString() == task.Id);
        Assert.Equal("completed", record.GetProperty("status").GetString());
        Assert.Equal("R17", record.GetProperty("assignedRobot").GetString());
        Assert.Equal(start, record.GetProperty("startedAt").GetDateTimeOffset());
        Assert.Equal(finish, record.GetProperty("finishedAt").GetDateTimeOffset());
    }

    [Fact]
    public async Task MissingScheduledAt_ReturnsBadRequest()
    {
        using var client = await factory.CreateSessionClientAsync();
        var response = await client.PostAsJsonAsync("/api/v1/task", new { taskType = "medication_delivery", source = "pharmacy", destination = "ward_a_2", priority = "normal" });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task RejectsTaskLocationsOutsideProfile()
    {
        using var client = await factory.CreateSessionClientAsync();
        var response = await client.PostAsJsonAsync("/api/v1/task", new {
            taskType = "medication_delivery", source = "pharmacy", destination = "waste_return_2",
            priority = "normal", scheduledAt = DateTimeOffset.UtcNow.AddHours(1)
        });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

}

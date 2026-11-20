using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Server.Models;
using Server.Services;
using Server.Services.Tasks;
using Xunit;

namespace Server.Tests.Unit.Services;

public class RosTaskStatusTests
{
    [Fact]
    public async Task PublishedTaskSummaryUpdatesSharedTaskAndUsesActualRosTimes()
    {
        using var provider = CreateProvider();
        using var scope = provider.CreateScope();
        var tasks = scope.ServiceProvider.GetRequiredService<ITaskService>();
        var task = await tasks.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        task.Dispatched = true;
        using var bridge = new RosBridgeTestService(NullLogger<RosBridgeTestService>.Instance,
            new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string,string?> { ["TaskDispatch:AcceptLegacyRmfDispatchReports"] = "true" }).Build(), provider.GetRequiredService<RobotStateStore>(), provider.GetRequiredService<IServiceScopeFactory>());
        var start = DateTimeOffset.UtcNow.AddMinutes(-2);
        start = DateTimeOffset.FromUnixTimeSeconds(start.ToUnixTimeSeconds());
        var finish = start.AddMinutes(1);

        await bridge.ProcessMessageAsync(Summary(task.Id, 0, start, finish));
        Assert.Equal(RobotTaskStatus.Pending, task.Status);
        Assert.Null(task.StartedAt);
        Assert.Null(task.FinishedAt);

        await bridge.ProcessMessageAsync(Dispatch(task.Id, 2));
        Assert.Equal(RobotTaskStatus.Pending, task.Status);
        await bridge.ProcessMessageAsync(Dispatch(task.Id, 3));
        Assert.Equal(RobotTaskStatus.Assigned, task.Status);
        Assert.Equal("robot-a", task.AssignedRobot);

        await bridge.ProcessMessageAsync(Summary(task.Id, 1, start, finish));
        Assert.Equal(RobotTaskStatus.Running, task.Status);
        Assert.Equal(start, task.StartedAt);
        Assert.Null(task.FinishedAt); // An active summary's end time is an estimate.
        Assert.Equal("robot-a", task.AssignedRobot);
        await bridge.ProcessMessageAsync(Dispatch(task.Id, 3));
        await bridge.ProcessMessageAsync(Summary(task.Id, 0, start, finish));
        Assert.Equal(RobotTaskStatus.Running, task.Status);

        await bridge.ProcessMessageAsync(Summary(task.Id, 2, start, finish));
        Assert.Equal(RobotTaskStatus.Completed, task.Status);
        Assert.Equal(finish, task.FinishedAt);
        await bridge.ProcessMessageAsync(Summary(task.Id, 1, start, finish));
        Assert.Equal(RobotTaskStatus.Completed, task.Status);
        Assert.Equal(finish, task.FinishedAt);
    }

    [Fact]
    public async Task ExplicitDispatchFailureIsTerminalButUnknownDispatchIsIgnored()
    {
        using var provider = CreateProvider();
        using var scope = provider.CreateScope();
        var tasks = scope.ServiceProvider.GetRequiredService<ITaskService>();
        var task = await tasks.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        task.Dispatched = true;
        using var bridge = new RosBridgeTestService(NullLogger<RosBridgeTestService>.Instance,
            new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string,string?> { ["TaskDispatch:AcceptLegacyRmfDispatchReports"] = "true" }).Build(), provider.GetRequiredService<RobotStateStore>(), provider.GetRequiredService<IServiceScopeFactory>());
        await bridge.ProcessMessageAsync(Dispatch(task.Id, 1));
        Assert.Equal(RobotTaskStatus.Pending, task.Status);
        await bridge.ProcessMessageAsync(Dispatch(task.Id, 4));
        Assert.Equal(RobotTaskStatus.Failed, task.Status);
        Assert.Null(task.StartedAt);
        Assert.NotNull(task.FinishedAt);
        await bridge.ProcessMessageAsync(Dispatch(task.Id, 3));
        Assert.Equal(RobotTaskStatus.Failed, task.Status);
    }

    [Theory]
    [InlineData(3, RobotTaskStatus.Failed)]
    [InlineData(4, RobotTaskStatus.Cancelled)]
    public async Task TerminalReportWithoutActualStartLeavesStartedAtNull(int state, RobotTaskStatus expected)
    {
        using var provider = CreateProvider();
        using var scope = provider.CreateScope();
        var tasks = scope.ServiceProvider.GetRequiredService<ITaskService>();
        var task = await tasks.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        using var json = JsonDocument.Parse(JsonSerializer.Serialize(new { task_id = task.Id, state,
            start_time = new { sec = 0, nanosec = 0 }, end_time = new { sec = DateTimeOffset.UtcNow.ToUnixTimeSeconds(), nanosec = 0 } }));
        await scope.ServiceProvider.GetRequiredService<RosTaskStatusHandler>().HandleAsync(json.RootElement);
        Assert.Equal(expected, task.Status);
        Assert.Null(task.StartedAt);
        Assert.NotNull(task.FinishedAt);
    }

    [Fact]
    public async Task UnknownTaskOrUnknownStateDoesNotCreateOrChangeTasks()
    {
        using var provider = CreateProvider();
        using var scope = provider.CreateScope();
        var tasks = scope.ServiceProvider.GetRequiredService<ITaskService>();
        var task = await tasks.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        var handler = scope.ServiceProvider.GetRequiredService<RosTaskStatusHandler>();
        using var unknown = JsonDocument.Parse("{\"task_id\":\"unknown\",\"state\":2}");
        using var invalid = JsonDocument.Parse(JsonSerializer.Serialize(new { task_id = task.Id, state = 999 }));
        await handler.HandleAsync(unknown.RootElement);
        await handler.HandleAsync(invalid.RootElement);
        Assert.Single(await tasks.GetTasksAsync());
        Assert.Equal(RobotTaskStatus.Pending, task.Status);
    }

    [Fact]
    public async Task RmfAssignmentReportsAreIgnoredByDefault()
    {
        using var provider = CreateProvider();
        using var scope = provider.CreateScope();
        var tasks = scope.ServiceProvider.GetRequiredService<ITaskService>();
        var task = await tasks.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        task.Dispatched = true;
        using var bridge = new RosBridgeTestService(NullLogger<RosBridgeTestService>.Instance,
            new ConfigurationBuilder().Build(), provider.GetRequiredService<RobotStateStore>(), provider.GetRequiredService<IServiceScopeFactory>());
        await bridge.ProcessMessageAsync(Dispatch(task.Id, 3));
        Assert.Equal(RobotTaskStatus.Pending, task.Status);
        Assert.Null(task.AssignedRobot);
    }

    private static string Summary(string id, int state, DateTimeOffset start, DateTimeOffset finish)
        => JsonSerializer.Serialize(new { op = "publish", topic = "/task_summaries", msg = new {
            task_id = id, state, robot_name = "hospital_robot_1",
            start_time = new { sec = start.ToUnixTimeSeconds(), nanosec = 0 },
            end_time = new { sec = finish.ToUnixTimeSeconds(), nanosec = 0 }
        }});

    private static string Dispatch(string id, int status)
        => JsonSerializer.Serialize(new { op = "publish", topic = "/dispatch_states", msg = new {
            task_id = id, status, assignment = new { is_assigned = status == 3,
                fleet_name = "hospital", expected_robot_name = "hospital_robot_1" }
        }});

    private static ServiceProvider CreateProvider()
    {
        var services = new ServiceCollection();
        services.AddLogging();
        services.AddHttpClient();
        services.AddSingleton<IConfiguration>(new ConfigurationBuilder().Build());
        services.AddSingleton<TaskStore>();
        services.AddSingleton<RobotStateStore>();
        services.AddScoped<ITaskDispatcher, HttpTaskDispatcher>();
        services.AddScoped<ITaskService, TaskService>();
        services.AddScoped<RosTaskStatusHandler>();
        return services.BuildServiceProvider(new ServiceProviderOptions { ValidateScopes = true });
    }
}

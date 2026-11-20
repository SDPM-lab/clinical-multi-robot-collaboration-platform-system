using Xunit;

using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Server.Services;
using Server.Services.Tasks;
using Server.Models;
using Server.Requests;

namespace Server.Tests.Unit.Services;

public class TaskServiceTests
{
    [Fact]
    public async Task DevelopmentSimulationShowsAssignmentStagesWithoutInventingTelemetry()
    {
        var service = new TaskService(new TaskStore(),
            new HttpTaskDispatcher(new TestHttpClientFactory(), new ConfigurationBuilder().Build(), NullLogger<HttpTaskDispatcher>.Instance),
            NullLogger<TaskService>.Instance);
        var robots = new RobotStateStore();
        var task = await service.CreateTaskAsync(new() { Source = "pharmacy", Destination = "ward_a_1",
            ScheduledAt = DateTimeOffset.UtcNow.AddMinutes(1) });
        task.ScheduledAt = DateTimeOffset.UtcNow.AddSeconds(-1);
        await service.SimulateDueTasksAsync(robots, default);
        Assert.Equal(RobotTaskStatus.Assigned, task.Status);
        Assert.Equal("robot-a", task.AssignedRobot);
        Assert.True(task.IsSimulated);
        await service.SimulateDueTasksAsync(robots, default);
        Assert.Equal(RobotTaskStatus.Running, task.Status);
        Assert.NotNull(task.StartedAt);
        Assert.All(robots.GetAll(), robot => Assert.False(robot.HasTelemetry));
        Assert.Equal(SimulatedArrivalResult.Forbidden,
            await service.CompleteSimulatedArrivalAsync(task.Id, "robot-a", "pharmacy", "reception_back"));
        Assert.Equal(RobotTaskStatus.Running, task.Status);
        Assert.Equal(SimulatedArrivalResult.Success,
            await service.CompleteSimulatedArrivalAsync(task.Id, "robot-a", "pharmacy", "ward_a_1"));
        Assert.Equal(RobotTaskStatus.Completed, task.Status);
        Assert.NotNull(task.FinishedAt);
        Assert.Equal(SimulatedArrivalResult.Forbidden,
            await service.CompleteSimulatedArrivalAsync(task.Id, "robot-a", "pharmacy", "ward_a_1"));
    }
    [Fact]
    public async Task FutureTaskIsAssignedImmediatelyButDoesNotStartEarly()
    {
        var service = CreateService();
        var robots = new RobotStateStore();
        var task = await service.CreateTaskAsync(new() { Source = "pharmacy", Destination = "ward_a_1",
            ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        await service.SimulateDueTasksAsync(robots, default);
        Assert.Equal(RobotTaskStatus.Assigned, task.Status);
        Assert.Equal("robot-a", task.AssignedRobot);
        Assert.Null(task.StartedAt);
        await service.SimulateDueTasksAsync(robots, default);
        Assert.Equal(RobotTaskStatus.Assigned, task.Status);
        Assert.Null(task.StartedAt);
    }
    [Theory]
    [InlineData(TaskType.WasteTransport, "robot-a")]
    [InlineData(TaskType.ClothesCollection, "robot-a")]
    [InlineData(TaskType.MedicationDelivery, "robot-hospital_robot_3")]
    [InlineData(TaskType.SpecimenDelivery, "robot-hospital_robot_3")]
    [InlineData(TaskType.WardService, "robot-hospital_robot_6")]
    public async Task SimulationUsesCompatibleRobotProfile(TaskType type, string expectedRobot)
    {
        var service = CreateService();
        var task = await service.CreateTaskAsync(new() { TaskType = type, ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        await service.SimulateDueTasksAsync(new RobotStateStore(), default);
        Assert.Equal(expectedRobot, task.AssignedRobot);
        Assert.Equal(RobotTaskStatus.Assigned, task.Status);
    }
    [Theory]
    [InlineData(999, 1)]
    [InlineData(0, 999)]
    public async Task CreateRejectsUndefinedEnumsWithoutSaving(int type, int priority)
    {
        var service = CreateService();
        await Assert.ThrowsAsync<ArgumentException>(() => service.CreateTaskAsync(new()
        {
            TaskType = (TaskType)type, Priority = (TaskPriority)priority,
            ScheduledAt = DateTimeOffset.UtcNow.AddHours(1)
        }));
        Assert.Empty(await service.GetTasksAsync());
    }

    [Fact]
    public async Task ScheduleCanBeUpdatedAndDeletedBeforeDispatch()
    {
        var service = CreateService();
        var initial = DateTimeOffset.UtcNow.AddHours(1);
        await service.CreateTaskAsync(new CreateTaskRequest
        {
            Source = "pharmacy", Destination = "ward_a", ScheduledAt = initial,
            TaskType = TaskType.MedicationDelivery
        });
        var task = Assert.Single(await service.GetTasksAsync(), t => t.ScheduledAt == initial);
        Assert.Null(task.AssignedRobot);
        var updated = initial.AddHours(1);
        var outcome = await service.UpdateTaskScheduleAsync(task.Id, new UpdateTaskScheduleRequest { ScheduledAt = updated });
        Assert.Equal(UpdateTaskScheduleResult.Success, outcome.Result);
        var replacement = Assert.IsType<RobotTask>(outcome.Replacement);
        Assert.NotEqual(task.Id, replacement.Id);
        Assert.NotEqual(task.TaskCode, replacement.TaskCode);
        Assert.Null(await service.GetTaskByIdAsync(task.Id));
        Assert.Equal(updated, replacement.ScheduledAt);
        Assert.Equal(task.TaskType, replacement.TaskType);
        Assert.Equal(task.Priority, replacement.Priority);
        Assert.Null(replacement.AssignedRobot);
        Assert.Null(replacement.RequestedRobotId);
        Assert.Equal(RobotTaskStatus.Pending, replacement.Status);
        Assert.False(await service.UpdateTaskDispatchAsync(task.Id, true, "old-robot"));
        Assert.Equal(DeleteTaskResult.Success, await service.DeleteTaskAsync(replacement.Id));

    }

    [Fact]
    public async Task ScheduleRejectsMissingPastUnknownAndRunningTasks()
    {
        var service = CreateService();
        await Assert.ThrowsAsync<ArgumentException>(() => service.UpdateTaskScheduleAsync("task-2", new()));
        await Assert.ThrowsAsync<ArgumentException>(() => service.UpdateTaskScheduleAsync("task-2",
            new() { ScheduledAt = DateTimeOffset.UtcNow.AddMinutes(-1) }));
        var request = new UpdateTaskScheduleRequest { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) };
        Assert.Equal(UpdateTaskScheduleResult.NotFound, (await service.UpdateTaskScheduleAsync("unknown", request)).Result);
        var initial = DateTimeOffset.UtcNow.AddHours(3);
        await service.CreateTaskAsync(new() { Source = "pharmacy", Destination = "ward_a", ScheduledAt = initial });
        var running = Assert.Single(await service.GetTasksAsync(), t => t.ScheduledAt == initial);
        await service.UpdateTaskStatusAsync(running.Id, RobotTaskStatus.Running);
        Assert.Equal(UpdateTaskScheduleResult.Forbidden, (await service.UpdateTaskScheduleAsync(running.Id, request)).Result);
    }

    [Fact]
    public async Task WorkerDispatchesNewTasksOnceAndPreventsEditingAfterDispatch()
    {
        var factory = new RecordingHttpClientFactory();
        var service = new TaskService(new TaskStore(), new HttpTaskDispatcher(factory, DispatchConfiguration(), NullLogger<HttpTaskDispatcher>.Instance), NullLogger<TaskService>.Instance);
        var initial = DateTimeOffset.UtcNow.AddHours(1);
        await service.CreateTaskAsync(new() { Source = "pharmacy", Destination = "ward_a", ScheduledAt = initial });
        await service.DispatchDueTasksAsync(default);
        Assert.Equal(1, factory.Requests);
        var task = Assert.Single(await service.GetTasksAsync(), t => t.ScheduledAt == initial);
        task.ScheduledAt = DateTimeOffset.UtcNow.AddSeconds(-1);
        await service.DispatchDueTasksAsync(default);
        await service.DispatchDueTasksAsync(default);
        Assert.Equal(1, factory.Requests);
        Assert.Equal(RobotTaskStatus.Pending, task.Status);
        Assert.True(task.Dispatched);
        Assert.True(await service.UpdateTaskDispatchAsync(task.Id, assigned: true, robotId: "robot-a"));
        Assert.Equal(RobotTaskStatus.Assigned, task.Status);
        Assert.Equal("robot-a", task.AssignedRobot);
        await Assert.ThrowsAsync<InvalidOperationException>(() => service.UpdateTaskScheduleAsync(task.Id,
            new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(2) }));
        Assert.Equal(DeleteTaskResult.Forbidden, await service.DeleteTaskAsync(task.Id));
    }

    [Fact]
    public async Task ConcurrentCreationGeneratesUniqueTaskCodes()
    {
        var service = CreateService();
        var tasks = await Task.WhenAll(Enumerable.Range(0, 20).Select(_ => Task.Run(() =>
            service.CreateTaskAsync(new() { Source = "pharmacy", Destination = "lab", ScheduledAt = DateTimeOffset.UtcNow.AddDays(2) }))));
        Assert.Equal(20, tasks.Select(task => task.TaskCode).Distinct().Count());
        foreach (var task in tasks)
        {
            Assert.Matches(@"^T\d{4,}$", task.TaskCode);
            await service.DeleteTaskAsync(task.Id);
        }
    }

    [Fact]
    public async Task RequestedRobotIsNotReportedAsAssignedBeforeRmfConfirmation()
    {
        var service = CreateService();
        var task = await service.CreateTaskAsync(new() {
            RobotId = "robot-a", ScheduledAt = DateTimeOffset.UtcNow.AddHours(1)
        });
        Assert.Equal("robot-a", task.RequestedRobotId);
        Assert.Null(task.AssignedRobot);
        Assert.Equal(RobotTaskStatus.Pending, task.Status);
    }

    [Fact]
    public async Task DifferentServiceInstancesShareTasksAndDispatchLockThroughStore()
    {
        using var store = new TaskStore();
        var factory = new RecordingHttpClientFactory();
        var client = new HttpTaskDispatcher(factory, DispatchConfiguration(), NullLogger<HttpTaskDispatcher>.Instance);
        var first = new TaskService(store, client, NullLogger<TaskService>.Instance);
        var second = new TaskService(store, client, NullLogger<TaskService>.Instance);
        var task = await first.CreateTaskAsync(new() { Source = "pharmacy", Destination = "lab", ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        Assert.Same(task, await second.GetTaskByIdAsync(task.Id));
        task.ScheduledAt = DateTimeOffset.UtcNow.AddSeconds(-1);
        await Task.WhenAll(first.DispatchDueTasksAsync(default), second.DispatchDueTasksAsync(default));
        Assert.Equal(1, factory.Requests);
    }

    [Fact]
    public async Task RecordsFirstStartAndFinishAndIgnoresLateOrRepeatedReports()
    {
        var service = CreateService();
        var task = await service.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        Assert.Null(task.StartedAt);
        Assert.Null(task.FinishedAt);
        await service.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Assigned);
        Assert.Null(task.StartedAt);
        await service.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Running);
        var started = task.StartedAt;
        Assert.NotNull(started);
        await service.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Running, startedAt: started!.Value.AddMinutes(1));
        Assert.Equal(started, task.StartedAt);
        Assert.False(await service.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Assigned));
        await service.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Completed);
        var finished = task.FinishedAt;
        Assert.NotNull(finished);
        await service.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Completed, finishedAt: finished!.Value.AddMinutes(1));
        Assert.Equal(finished, task.FinishedAt);
        Assert.False(await service.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Running));
        Assert.Equal(RobotTaskStatus.Completed, task.Status);
    }

    [Theory]
    [InlineData(RobotTaskStatus.Failed)]
    [InlineData(RobotTaskStatus.Cancelled)]
    public async Task EndingBeforeExecutionDoesNotInventAStartTime(RobotTaskStatus status)
    {
        var service = CreateService();
        var task = await service.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        await service.UpdateTaskStatusAsync(task.Id, status);
        Assert.Null(task.StartedAt);
        Assert.NotNull(task.FinishedAt);
    }

    [Fact]
    public async Task DispatchFailureRecordsFinishWithoutStart()
    {
        var factory = new RecordingHttpClientFactory { ResponseStatus = System.Net.HttpStatusCode.BadRequest };
        var service = new TaskService(new TaskStore(), new HttpTaskDispatcher(factory, DispatchConfiguration(), NullLogger<HttpTaskDispatcher>.Instance), NullLogger<TaskService>.Instance);
        var task = await service.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        task.ScheduledAt = DateTimeOffset.UtcNow.AddSeconds(-1);
        await service.DispatchDueTasksAsync(default);
        Assert.Equal(RobotTaskStatus.Failed, task.Status);
        Assert.Null(task.StartedAt);
        Assert.NotNull(task.FinishedAt);
    }

    [Fact]
    public async Task UnknownDeliveryResultStaysUnconfirmedAndDoesNotRetry()
    {
        var factory = new RecordingHttpClientFactory { ThrowOnSend = true };
        var service = new TaskService(new TaskStore(), new HttpTaskDispatcher(factory, DispatchConfiguration(), NullLogger<HttpTaskDispatcher>.Instance), NullLogger<TaskService>.Instance);
        var task = await service.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        task.ScheduledAt = DateTimeOffset.UtcNow.AddSeconds(-1);
        await service.DispatchDueTasksAsync(default);
        await service.DispatchDueTasksAsync(default);
        Assert.Equal(1, factory.Requests);
        Assert.Equal(RobotTaskStatus.Pending, task.Status);
        Assert.Null(task.StartedAt);
        Assert.Null(task.FinishedAt);
        Assert.True(await service.UpdateTaskDispatchAsync(task.Id, assigned: true, robotId: "robot-a"));
        Assert.Equal(RobotTaskStatus.Assigned, task.Status);
    }

    [Fact]
    public async Task ExplicitAssignmentFailureEndsTaskWithoutStartingIt()
    {
        var factory = new RecordingHttpClientFactory();
        var service = new TaskService(new TaskStore(), new HttpTaskDispatcher(factory, DispatchConfiguration(), NullLogger<HttpTaskDispatcher>.Instance), NullLogger<TaskService>.Instance);
        var task = await service.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        Assert.False(await service.UpdateTaskDispatchAsync(task.Id, assigned: true, robotId: "robot-a"));
        task.ScheduledAt = DateTimeOffset.UtcNow.AddSeconds(-1);
        await service.DispatchDueTasksAsync(default);
        Assert.True(await service.UpdateTaskDispatchAsync(task.Id, assigned: false));
        Assert.Equal(RobotTaskStatus.Failed, task.Status);
        Assert.Null(task.StartedAt);
        Assert.NotNull(task.FinishedAt);
    }

    [Fact]
    public async Task PriorityChangesOnlyForPendingUndispatchedTasks()
    {
        var service = CreateService();
        var task = await service.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        var high = new UpdateTaskPriorityRequest { Priority = TaskPriority.High };
        Assert.Equal(UpdateTaskPriorityResult.Success, await service.UpdateTaskPriorityAsync(task.Id, high));
        Assert.Equal(TaskPriority.High, (await service.GetTaskByIdAsync(task.Id))!.Priority);
        Assert.Equal(UpdateTaskPriorityResult.NotFound, await service.UpdateTaskPriorityAsync("missing", high));
        await Assert.ThrowsAsync<ArgumentException>(() => service.UpdateTaskPriorityAsync(task.Id, new()));
        await Assert.ThrowsAsync<ArgumentException>(() => service.UpdateTaskPriorityAsync(task.Id, new() { Priority = (TaskPriority)99 }));
        await service.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Assigned);
        Assert.Equal(UpdateTaskPriorityResult.Forbidden, await service.UpdateTaskPriorityAsync(task.Id, new() { Priority = TaskPriority.Emergency }));
        Assert.Equal(TaskPriority.High, task.Priority);
    }

    [Theory]
    [InlineData(RobotTaskStatus.Running)]
    public async Task SubmittedTasksCannotBeCancelledRescheduledOrDeleted(RobotTaskStatus status)
    {
        var service = CreateService();
        var task = await service.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        await service.UpdateTaskStatusAsync(task.Id, status);
        Assert.Equal(CancelTaskResult.Forbidden, await service.CancelPendingTaskAsync(task.Id));
        Assert.Equal(UpdateTaskScheduleResult.Forbidden, (await service.UpdateTaskScheduleAsync(task.Id,
            new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(2) })).Result);
        Assert.Equal(DeleteTaskResult.Forbidden, await service.DeleteTaskAsync(task.Id));
        Assert.Equal(status, task.Status);
        Assert.Single(await service.GetTasksAsync());
    }

    [Fact]
    public async Task UnconfiguredDispatcherKeepsDueTaskPendingWithoutContactingOldBridge()
    {
        var factory = new RecordingHttpClientFactory();
        var service = new TaskService(new TaskStore(), new HttpTaskDispatcher(factory,
            new ConfigurationBuilder().Build(), NullLogger<HttpTaskDispatcher>.Instance), NullLogger<TaskService>.Instance);
        var task = await service.CreateTaskAsync(new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        task.ScheduledAt = DateTimeOffset.UtcNow.AddSeconds(-1);
        await service.DispatchDueTasksAsync(default);
        Assert.Equal(0, factory.Requests);
        Assert.Equal(RobotTaskStatus.Pending, task.Status);
        Assert.False(task.Dispatched);
    }

    [Fact]
    public async Task AssignedUnstartedTaskCanBeRequeuedLocallyButCannotBeCancelled()
    {
        var service = new TaskService(new TaskStore(), new HttpTaskDispatcher(new RecordingHttpClientFactory(),
            new ConfigurationBuilder().Build(), NullLogger<HttpTaskDispatcher>.Instance), NullLogger<TaskService>.Instance);
        var task = await service.CreateTaskAsync(new() { Source = "pharmacy", Destination = "lab", RobotId = "preferred", Note = "handoff", ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        await service.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Assigned, robotId: "robot-a");
        Assert.Equal(CancelTaskResult.Forbidden, await service.CancelPendingTaskAsync(task.Id));
        var result = await service.UpdateTaskScheduleAsync(task.Id, new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(2) });
        Assert.Equal(UpdateTaskScheduleResult.Success, result.Result);
        Assert.Null(await service.GetTaskByIdAsync(task.Id));
        Assert.Null(result.Replacement!.AssignedRobot);
        Assert.Null(result.Replacement.RequestedRobotId);
        Assert.Null(result.Replacement.StartedAt);
        Assert.Equal("handoff", result.Replacement.Note);
        Assert.Equal(RobotTaskStatus.Pending, result.Replacement.Status);
        Assert.False(await service.UpdateTaskStatusAsync(task.Id, RobotTaskStatus.Running));
    }

    private static IConfiguration DispatchConfiguration() => new ConfigurationBuilder()
        .AddInMemoryCollection(new Dictionary<string, string?> { ["TaskDispatch:Endpoint"] = "http://dispatcher.test/tasks" }).Build();

    private sealed class RecordingHttpClientFactory : HttpMessageHandler, IHttpClientFactory
    {
        public int Requests { get; private set; }
        public System.Net.HttpStatusCode ResponseStatus { get; init; } = System.Net.HttpStatusCode.OK;
        public bool ThrowOnSend { get; init; }
        public HttpClient CreateClient(string name) => new(this, disposeHandler: false);
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            Requests++;
            if (ThrowOnSend) throw new HttpRequestException("Response unavailable");
            return Task.FromResult(new HttpResponseMessage(ResponseStatus) { Content = new StringContent("{}") });
        }
    }

    private static TaskService CreateService()
    {
        var httpClientFactory = new TestHttpClientFactory();

        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["TaskDispatch:Endpoint"] = "http://dispatcher.test/tasks"
            })
            .Build();

        var logger = NullLogger<TaskService>.Instance;

        return new TaskService(
            new TaskStore(),
            new HttpTaskDispatcher(httpClientFactory, configuration, NullLogger<HttpTaskDispatcher>.Instance),
            logger
        );
    }

    private sealed class TestHttpClientFactory : IHttpClientFactory
    {
        public HttpClient CreateClient(string name)
        {
            return new HttpClient();
        }
    }
}

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
    public async Task ScheduleCanBeUpdatedAndDeletedBeforeDispatch()
    {
        var service = CreateService();
        var initial = DateTimeOffset.UtcNow.AddHours(1);
        await service.CreateTaskAsync(new CreateTaskRequest
        {
            Origin = "pharmacy", Destination = "ward_a", ScheduledAt = initial,
            TaskType = TaskType.MedicineDelivery
        });
        var task = Assert.Single(await service.GetTasksAsync(), t => t.ScheduledAt == initial);
        Assert.Null(task.AssignedRobot);
        var updated = initial.AddHours(1);
        Assert.Equal(UpdateTaskScheduleResult.Success, await service.UpdateTaskScheduleAsync(task.Id,
            new UpdateTaskScheduleRequest { ScheduledAt = updated }));
        Assert.Equal(updated, (await service.GetTaskByIdAsync(task.Id))!.ScheduledAt);
        Assert.Equal(DeleteTaskResult.Success, await service.DeleteTaskAsync(task.Id));
        Assert.Null(await service.GetTaskByIdAsync(task.Id));
    }

    [Fact]
    public async Task ScheduleRejectsMissingPastUnknownAndRunningTasks()
    {
        var service = CreateService();
        await Assert.ThrowsAsync<ArgumentException>(() => service.UpdateTaskScheduleAsync("task-2", new()));
        await Assert.ThrowsAsync<ArgumentException>(() => service.UpdateTaskScheduleAsync("task-2",
            new() { ScheduledAt = DateTimeOffset.UtcNow.AddMinutes(-1) }));
        var request = new UpdateTaskScheduleRequest { ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) };
        Assert.Equal(UpdateTaskScheduleResult.NotFound, await service.UpdateTaskScheduleAsync("unknown", request));
        var initial = DateTimeOffset.UtcNow.AddHours(3);
        await service.CreateTaskAsync(new() { Origin = "pharmacy", Destination = "ward_a", ScheduledAt = initial });
        var running = Assert.Single(await service.GetTasksAsync(), t => t.ScheduledAt == initial);
        await service.UpdateTaskStatusAsync(running.Id, RobotTaskStatus.Running);
        Assert.Equal(UpdateTaskScheduleResult.Forbidden, await service.UpdateTaskScheduleAsync(running.Id, request));
    }

    [Fact]
    public async Task WorkerDispatchesOnlyDueTasksOnceAndPreventsEditingAfterDispatch()
    {
        var factory = new RecordingHttpClientFactory();
        var service = new TaskService(new TaskStore(), new RosTaskClient(factory, new ConfigurationBuilder().Build(), NullLogger<RosTaskClient>.Instance), NullLogger<TaskService>.Instance);
        var initial = DateTimeOffset.UtcNow.AddHours(1);
        await service.CreateTaskAsync(new() { Origin = "pharmacy", Destination = "ward_a", ScheduledAt = initial });
        await service.DispatchDueTasksAsync(default);
        Assert.Equal(0, factory.Requests);
        var task = Assert.Single(await service.GetTasksAsync(), t => t.ScheduledAt == initial);
        task.ScheduledAt = DateTimeOffset.UtcNow.AddSeconds(-1);
        await service.DispatchDueTasksAsync(default);
        await service.DispatchDueTasksAsync(default);
        Assert.Equal(1, factory.Requests);
        Assert.Equal(RobotTaskStatus.Assigned, task.Status);
        Assert.Equal(UpdateTaskScheduleResult.Forbidden, await service.UpdateTaskScheduleAsync(task.Id,
            new() { ScheduledAt = DateTimeOffset.UtcNow.AddHours(2) }));
        Assert.Equal(DeleteTaskResult.Forbidden, await service.DeleteTaskAsync(task.Id));
    }

    [Fact]
    public async Task ConcurrentCreationGeneratesUniqueTaskCodes()
    {
        var service = CreateService();
        var tasks = await Task.WhenAll(Enumerable.Range(0, 20).Select(_ => Task.Run(() =>
            service.CreateTaskAsync(new() { Origin = "pharmacy", Destination = "lab", ScheduledAt = DateTimeOffset.UtcNow.AddDays(2) }))));
        Assert.Equal(20, tasks.Select(task => task.TaskCode).Distinct().Count());
        foreach (var task in tasks)
        {
            Assert.Matches(@"^T\d{4,}$", task.TaskCode);
            await service.DeleteTaskAsync(task.Id);
        }
    }

    [Fact]
    public async Task DifferentServiceInstancesShareTasksAndDispatchLockThroughStore()
    {
        using var store = new TaskStore();
        var factory = new RecordingHttpClientFactory();
        var client = new RosTaskClient(factory, new ConfigurationBuilder().Build(), NullLogger<RosTaskClient>.Instance);
        var first = new TaskService(store, client, NullLogger<TaskService>.Instance);
        var second = new TaskService(store, client, NullLogger<TaskService>.Instance);
        var task = await first.CreateTaskAsync(new() { Origin = "pharmacy", Destination = "lab", ScheduledAt = DateTimeOffset.UtcNow.AddHours(1) });
        Assert.Same(task, await second.GetTaskByIdAsync(task.Id));
        task.ScheduledAt = DateTimeOffset.UtcNow.AddSeconds(-1);
        await Task.WhenAll(first.DispatchDueTasksAsync(default), second.DispatchDueTasksAsync(default));
        Assert.Equal(1, factory.Requests);
    }

    private sealed class RecordingHttpClientFactory : HttpMessageHandler, IHttpClientFactory
    {
        public int Requests { get; private set; }
        public HttpClient CreateClient(string name) => new(this, disposeHandler: false);
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            Requests++;
            return Task.FromResult(new HttpResponseMessage(System.Net.HttpStatusCode.OK) { Content = new StringContent("{}") });
        }
    }

    private static TaskService CreateService()
    {
        var httpClientFactory = new TestHttpClientFactory();

        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["RosBridge:BaseUrl"] = "http://localhost:5050"
            })
            .Build();

        var logger = NullLogger<TaskService>.Instance;

        return new TaskService(
            new TaskStore(),
            new RosTaskClient(httpClientFactory, configuration, NullLogger<RosTaskClient>.Instance),
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
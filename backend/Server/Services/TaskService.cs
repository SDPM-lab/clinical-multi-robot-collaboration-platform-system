using Server.Models;
using Server.Requests;
using Server.Services.Tasks;

namespace Server.Services;

public class TaskService : ITaskService
{
    // Dependencies for task storage, ROS communication, and logging.
    private readonly TaskStore _store;
    private readonly RosTaskClient _rosTaskClient;
    private readonly ILogger<TaskService> _logger;

    // Receive dependencies from the application service container.
    public TaskService(TaskStore store, RosTaskClient rosTaskClient, ILogger<TaskService> logger)
    {
        _store = store;
        _rosTaskClient = rosTaskClient;
        _logger = logger;
    }

    // Return all stored tasks.
    public Task<List<RobotTask>> GetTasksAsync()
    {
        return Task.FromResult(_store.GetAll());
    }

    // Find a task by ID, or return null when it does not exist.
    public Task<RobotTask?> GetTaskByIdAsync(string taskId)
    {
        _store.TryGet(taskId, out var task);

        return Task.FromResult(task);
    }

    // Return the latest assigned or running task for each robot.
    public Task<Dictionary<string, RobotTask>> GetActiveTasksByRobotAsync()
    {
        var result =
            _store.GetAll()
                .Where(task =>
                    task.Status is
                        RobotTaskStatus.Assigned
                        or RobotTaskStatus.Running
                    &&
                    !string.IsNullOrEmpty(
                        task.AssignedRobot
                    )
                )
                .GroupBy(task =>
                    task.AssignedRobot!
                )
                .ToDictionary(
                    group => group.Key,
                    group =>
                        group
                            .OrderByDescending(
                                task => task.CreatedAt
                            )
                            .First()
                );

        return Task.FromResult(result);
    }

    // Validate the scheduled time, then create and store a pending task.
    public Task<RobotTask> CreateTaskAsync(CreateTaskRequest request)
    {
        if (request.ScheduledAt is null || request.ScheduledAt <= DateTimeOffset.UtcNow)
            throw new ArgumentException("Scheduled time must be in the future.");

        var task = new RobotTask
        {
            Id = Guid.NewGuid().ToString(),
            TaskCode = _store.NextTaskCode(),

            TaskType = request.TaskType,
            Source = request.Origin,
            Destination = request.Destination,
            Priority = request.Priority,

            RequiredCapabilities = GetRequiredCapabilities(request.TaskType),

            Status = RobotTaskStatus.Pending,

            AssignedRobot = request.RobotId,
            ScheduledAt = request.ScheduledAt,
            Note = request.Note,
            CreatedAt = DateTime.UtcNow,
        };

        _store.Add(task);
        return Task.FromResult(task);
    }

    // Update the schedule only for pending tasks that have not been dispatched.
    public async Task<UpdateTaskScheduleResult> UpdateTaskScheduleAsync(
        string taskId, UpdateTaskScheduleRequest request)
    {
        if (request.ScheduledAt is null || request.ScheduledAt <= DateTimeOffset.UtcNow)
            throw new ArgumentException("Scheduled time must be in the future.");

        await _store.DispatchGate.WaitAsync();
        try
        {
            if (!_store.TryGet(taskId, out var task))
                return UpdateTaskScheduleResult.NotFound;
            if (task.Status != RobotTaskStatus.Pending || task.Dispatched)
                return UpdateTaskScheduleResult.Forbidden;
            task.ScheduledAt = request.ScheduledAt;
            return UpdateTaskScheduleResult.Success;
        }
        finally
        {
            _store.DispatchGate.Release();
        }
    }

    // Delete only pending tasks that have not been dispatched.
    public async Task<DeleteTaskResult> DeleteTaskAsync(string taskId)
    {
        await _store.DispatchGate.WaitAsync();
        try
        {
            if (!_store.TryGet(taskId, out var task))
                return DeleteTaskResult.NotFound;
            if (task.Status != RobotTaskStatus.Pending || task.Dispatched)
                return DeleteTaskResult.Forbidden;
            _store.Remove(taskId);
            return DeleteTaskResult.Success;
        }
        finally
        {
            _store.DispatchGate.Release();
        }
    }

    // Update a task status while preventing concurrent dispatch changes.
    public async Task<bool> UpdateTaskStatusAsync(
        string taskId,
        RobotTaskStatus status)
    {
        await _store.DispatchGate.WaitAsync();
        try
        {
            if (!_store.TryGet(taskId, out var task))
                return false;
            task.Status = status;
            return true;
        }
        finally
        {
            _store.DispatchGate.Release();
        }
    }

    // Dispatch due pending tasks to the ROS bridge when called by the background worker.
    internal async Task DispatchDueTasksAsync(CancellationToken cancellationToken)
    {
        await _store.DispatchGate.WaitAsync(cancellationToken);
        try
        {
            foreach (var task in _store.GetAll().Where(task =>
                task.Status == RobotTaskStatus.Pending && !task.Dispatched &&
                task.ScheduledAt.HasValue && task.ScheduledAt <= DateTimeOffset.UtcNow))
            {
                cancellationToken.ThrowIfCancellationRequested();
                try
                {
                    await _rosTaskClient.SendAsync(task);
                    task.Dispatched = true;
                    task.Status = RobotTaskStatus.Assigned;
                }
                catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
                {
                    // Do not automatically retry an ambiguous submission: ROS may already have accepted it.
                    task.Status = RobotTaskStatus.Failed;
                    _logger.LogError(ex, "Scheduled task {TaskId} dispatch failed", task.Id);
                }
            }
        }
        finally
        {
            _store.DispatchGate.Release();
        }
    }

    // Map each task type to the robot capabilities it requires.
    private static List<RobotCapability> GetRequiredCapabilities(TaskType taskType)
    {
        return taskType switch
        {
            TaskType.MedicineDelivery =>
            [
                RobotCapability.Navigation,
                RobotCapability.MedicineDelivery
            ],

            TaskType.SpecimenDelivery =>
            [
                RobotCapability.Navigation,
                RobotCapability.SpecimenDelivery
            ],

            TaskType.GeneralDelivery =>
            [
                RobotCapability.Navigation,
                RobotCapability.GeneralDelivery
            ],

            TaskType.WasteCollection =>
            [
                RobotCapability.Navigation,
                RobotCapability.GeneralDelivery
            ],

            _ =>
            [
                RobotCapability.Navigation
            ]
        };
    }
}

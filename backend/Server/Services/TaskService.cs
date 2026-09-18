using System.Collections.Concurrent;
using System.Text;
using System.Text.Json;
using Server.Models;
using Server.Requests;

namespace Server.Services;

public class TaskService : ITaskService
{
    private static readonly ConcurrentDictionary<string, RobotTask> _store = new(SeedData());

    private readonly IHttpClientFactory _httpClientFactory;
    private readonly IConfiguration _configuration;
    private readonly ILogger<TaskService> _logger;

    public TaskService(
        IHttpClientFactory httpClientFactory,
        IConfiguration configuration,
        ILogger<TaskService> logger)
    {
        _httpClientFactory = httpClientFactory;
        _configuration = configuration;
        _logger = logger;
    }

    internal static void ResetForTests()
    {
        _store.Clear();

        foreach (var kv in SeedData())
            _store[kv.Key] = kv.Value;
    }

    private static IEnumerable<KeyValuePair<string, RobotTask>> SeedData() =>
        new[]
        {
            Seed(
                "task-1",
                "藥品配送",
                TaskType.MedicineDelivery,
                "pharmacy",
                "ward_a",
                TaskPriority.High,
                RobotTaskStatus.Running,
                "hospital_robot_1"
            ),

            Seed(
                "task-2",
                "檢體配送",
                TaskType.SpecimenDelivery,
                "ward_b",
                "lab",
                TaskPriority.Emergency,
                RobotTaskStatus.Pending
            ),

            Seed(
                "task-3",
                "一般物資配送",
                TaskType.GeneralDelivery,
                "storage",
                "nurse_station",
                TaskPriority.Normal,
                RobotTaskStatus.Pending
            ),

            Seed(
                "task-4",
                "垃圾回收",
                TaskType.WasteCollection,
                "ward_c",
                "storage",
                TaskPriority.Low,
                RobotTaskStatus.Completed,
                "hospital_robot_2"
            )
        }
        .Select(task => new KeyValuePair<string, RobotTask>(task.Id, task));

    private static RobotTask Seed(
        string id,
        string title,
        TaskType taskType,
        string source,
        string destination,
        TaskPriority priority,
        RobotTaskStatus status,
        string? assignedRobot = null)
    {
        return new RobotTask
        {
            Id = id,
            Title = title,

            TaskType = taskType,
            Source = source,
            Destination = destination,
            Priority = priority,

            RequiredCapabilities = GetRequiredCapabilities(taskType),

            Status = status,
            AssignedRobot = assignedRobot,

            CreatedAt = DateTime.UtcNow,

            Start = status == RobotTaskStatus.Running
                ? DateTime.Now
                : null,

            End = status == RobotTaskStatus.Completed
                ? DateTime.Now
                : null,

            Confirmed = status == RobotTaskStatus.Completed
        };
    }

    public Task<List<RobotTask>> GetTasksAsync()
    {
        return Task.FromResult(_store.Values.ToList());
    }

    public Task<RobotTask?> GetTaskByIdAsync(string taskId)
    {
        _store.TryGetValue(taskId, out var task);

        return Task.FromResult(task);
    }

    public async Task CreateTaskAsync(CreateTaskRequest request)
    {
        DateTime? start = null;

        if (!string.IsNullOrWhiteSpace(request.StartTime))
        {
            if (!TimeOnly.TryParse(request.StartTime, out var time))
                throw new ArgumentException("時間格式不符");

            start = DateTime.Today.Add(time.ToTimeSpan());

            if (start < DateTime.Now)
                throw new ArgumentException("開始時間不可早於現在");
        }

        var task = new RobotTask
        {
            Id = Guid.NewGuid().ToString(),

            TaskType = request.TaskType,
            Source = request.Source,
            Destination = request.Destination,
            Priority = request.Priority,

            RequiredCapabilities =
                GetRequiredCapabilities(request.TaskType),

            Status = RobotTaskStatus.Pending,

            AssignedRobot = null,

            CreatedAt = DateTime.UtcNow,

            Title = string.IsNullOrWhiteSpace(request.Title)
                ? request.TaskType.ToString()
                : request.Title,

            Items = request.Items,

            Start = start,

            Note = request.Note
        };

        await SendTaskToRosBridgeAsync(task);

        _store[task.Id] = task;
    }

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

    private async Task SendTaskToRosBridgeAsync(RobotTask task)
    {
        var bridgeBaseUrl =
            _configuration["RosBridge:BaseUrl"]
            ?? "http://localhost:5050";

        var bridgeUrl =
            $"{bridgeBaseUrl}/api/hospital/tasks";

        var payload = new
        {
            task_id = task.Id,

            task_type =
                ToSnakeCase(task.TaskType),

            source = task.Source,

            destination = task.Destination,

            priority = (int)task.Priority,

            required_capabilities =
                task.RequiredCapabilities
                    .Select(ToSnakeCase)
                    .ToList(),

            created_at =
                new DateTimeOffset(
                    task.CreatedAt
                ).ToUnixTimeMilliseconds()
                / 1000.0,

            note = task.Note
        };

        var json = JsonSerializer.Serialize(payload);

        _logger.LogInformation(
            "Forwarding task to ROS bridge: {Json}",
            json
        );

        var client =
            _httpClientFactory.CreateClient();

        try
        {
            using var content =
                new StringContent(
                    json,
                    Encoding.UTF8,
                    "application/json"
                );

            var response =
                await client.PostAsync(
                    bridgeUrl,
                    content
                );

            var responseBody =
                await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError(
                    "ROS bridge request failed. Status={Status}, Body={Body}",
                    response.StatusCode,
                    responseBody
                );

                var statusCode = (int)response.StatusCode;

                if (statusCode >= 400 && statusCode < 500)
                {
                    throw new ArgumentException(
                        $"ROS bridge rejected task: {statusCode} {responseBody}"
                    );
                }

                throw new InvalidOperationException(
                    $"ROS bridge unavailable: {statusCode} {responseBody}"
                );
            }

            _logger.LogInformation(
                "ROS bridge accepted task. Body={Body}",
                responseBody
            );
        }
        catch (ArgumentException)
        {
            throw;
        }
        catch (InvalidOperationException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(
                ex,
                "Failed to forward task to ROS bridge"
            );

            throw new InvalidOperationException(
                "Failed to connect to ROS bridge",
                ex
            );
        }
    }

    private static string ToSnakeCase(TaskType taskType)
    {
        return taskType switch
        {
            TaskType.MedicineDelivery => "medicine_delivery",
            TaskType.SpecimenDelivery => "specimen_delivery",
            TaskType.GeneralDelivery => "general_delivery",
            TaskType.WasteCollection => "waste_collection",
            _ => "general_delivery"
        };
    }

    private static string ToSnakeCase(RobotCapability capability)
    {
        return capability switch
        {
            RobotCapability.Navigation => "navigation",
            RobotCapability.GeneralDelivery => "general_delivery",
            RobotCapability.MedicineDelivery => "medicine_delivery",
            RobotCapability.SpecimenDelivery => "specimen_delivery",
            RobotCapability.Manipulation => "manipulation",
            _ => capability.ToString().ToLowerInvariant()
        };
    }

    public Task<DeleteTaskResult> DeleteTaskAsync(string taskId)
    {
        if (!_store.TryGetValue(taskId, out var task))
            return Task.FromResult(DeleteTaskResult.NotFound);

        if (task.Status != RobotTaskStatus.Pending)
            return Task.FromResult(DeleteTaskResult.Forbidden);

        _store.TryRemove(taskId, out _);

        return Task.FromResult(DeleteTaskResult.Success);
    }

    public Task<bool> UpdateTaskStatusAsync(
        string taskId,
        RobotTaskStatus status)
    {
        if (!_store.TryGetValue(taskId, out var task))
            return Task.FromResult(false);

        task.Status = status;

        if (status == RobotTaskStatus.Running
            && task.Start == null)
        {
            task.Start = DateTime.Now;
        }

        if (status is
            RobotTaskStatus.Completed
            or RobotTaskStatus.Failed
            or RobotTaskStatus.Cancelled)
        {
            task.End = DateTime.Now;
        }

        return Task.FromResult(true);
    }

    public Task<ConfirmTaskResult> ConfirmTaskAsync(string taskId)
    {
        if (!_store.TryGetValue(taskId, out var task))
            return Task.FromResult(ConfirmTaskResult.NotFound);

        if (task.Status is not (
            RobotTaskStatus.Completed
            or RobotTaskStatus.Failed
            or RobotTaskStatus.Cancelled))
        {
            return Task.FromResult(
                ConfirmTaskResult.WrongState
            );
        }

        task.Confirmed = true;

        return Task.FromResult(
            ConfirmTaskResult.Success
        );
    }

    public Task<bool?> GetConfirmAsync(string taskId)
    {
        if (!_store.TryGetValue(taskId, out var task))
            return Task.FromResult<bool?>(null);

        return Task.FromResult<bool?>(
            task.Confirmed
        );
    }

    public Task<Dictionary<string, RobotTask>>
        GetActiveTasksByRobotAsync()
    {
        var result =
            _store.Values
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
}
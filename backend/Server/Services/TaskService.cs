using System.Collections.Concurrent;
using System.Text;
using System.Text.Json;
using Server.Models;
using Server.Requests;

namespace Server.Services;

public class TaskService : ITaskService
{
    private static readonly HashSet<string> ValidItems = ["clean-object", "clean-stain", "coat-sterilize"];

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
            Seed("task-1", "3F 病房清物消汙",  "ward-3f",     ["clean-object", "clean-stain"],         9, 45, "robot-a", RobotTaskStatus.Process),
            Seed("task-2", "2F 病房鍍膜殺菌", "ward-2f",     ["coat-sterilize"],                      10,  0, "robot-b", RobotTaskStatus.Idle),
            Seed("task-3", "急診室清汙作業",  "emergency",   ["clean-stain"],                         11, 15, "robot-b", RobotTaskStatus.Idle),
            Seed("task-4", "1F 走廊鍍膜清物", "corridor-1f", ["coat-sterilize", "clean-object"],       8,  0, "robot-a", RobotTaskStatus.Complete, endHour: 9,  endMinute: 30, confirmed: true),
            Seed("task-5", "急診室鍍膜殺菌",  "emergency",   ["coat-sterilize"],                       7, 30, "robot-b", RobotTaskStatus.Abort,    endHour: 8,  endMinute:  0),
        }.Select(t => new KeyValuePair<string, RobotTask>(t.Id, t));

    private static RobotTask Seed(
        string id, string title, string place, List<string> items,
        int hour, int minute, string robot, RobotTaskStatus status,
        int? endHour = null, int? endMinute = null, bool confirmed = false) => new()
    {
        Id        = id,
        Title     = title,
        Place     = place,
        Items     = items,
        Start     = DateTime.Today.AddHours(hour).AddMinutes(minute),
        End       = endHour.HasValue
                        ? DateTime.Today.AddHours(endHour.Value).AddMinutes(endMinute ?? 0)
                        : null,
        Robot     = robot,
        Status    = status,
        Confirmed = confirmed,
    };

    public Task<List<RobotTask>> GetTasksAsync() =>
        Task.FromResult(_store.Values.ToList());

    public Task<RobotTask?> GetTaskByIdAsync(string taskId)
    {
        _store.TryGetValue(taskId, out var task);
        return Task.FromResult(task);
    }

    public async Task CreateTaskAsync(CreateTaskRequest request)
    {
        var invalidItems = request.Items.Where(i => !ValidItems.Contains(i)).ToList();
        if (invalidItems.Count > 0)
            throw new ArgumentException("系統不處理該事項");

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
            Id     = Guid.NewGuid().ToString(),
            Title  = request.Title,
            Place  = request.Place,
            Items  = request.Items,
            Start  = start,
            Note   = request.Note,
            Robot  = request.Robot,
            Status = RobotTaskStatus.Idle,
        };

        _store[task.Id] = task;

        await SendTaskToRosBridgeAsync(task);
    }

    private async Task SendTaskToRosBridgeAsync(RobotTask task)
    {
        var bridgeBaseUrl = _configuration["RosBridge:BaseUrl"] ?? "http://localhost:5050";
        var bridgeUrl = $"{bridgeBaseUrl}/api/hospital/tasks";

        var target = MapPlaceToRmfWaypoint(task.Place);

        var payload = new
        {
            target,
            priority = 1,
            task_type = "go_to_place",
            note = $"from medical-robot-platform, taskId={task.Id}, title={task.Title}"
        };

        var json = JsonSerializer.Serialize(payload);

        _logger.LogInformation("Forwarding task to ROS bridge: {Json}", json);

        var client = _httpClientFactory.CreateClient();

        try
        {
            using var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await client.PostAsync(bridgeUrl, content);
            var responseBody = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError(
                    "ROS bridge request failed. Status={Status}, Body={Body}",
                    response.StatusCode,
                    responseBody
                );
                return;
            }

            _logger.LogInformation("ROS bridge accepted task. Body={Body}", responseBody);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to forward task to ROS bridge");
        }
    }

    private static string MapPlaceToRmfWaypoint(string place)
    {
        return place switch
        {
            // 如果學長平台地點已經跟 RMF waypoint 一樣，會直接走 default。
            // 如果不一樣，就在這裡加對照。
            "ward-3f" => "ward_a",
            "ward-2f" => "ward_b",
            "emergency" => "procedure_room",
            "corridor-1f" => "nurse_station",

            _ => place
        };
    }

    public Task<DeleteTaskResult> DeleteTaskAsync(string taskId)
    {
        if (!_store.TryGetValue(taskId, out var task))
            return Task.FromResult(DeleteTaskResult.NotFound);
        if (task.Status != RobotTaskStatus.Idle)
            return Task.FromResult(DeleteTaskResult.Forbidden);
        _store.TryRemove(taskId, out _);
        return Task.FromResult(DeleteTaskResult.Success);
    }

    public Task<bool> UpdateTaskStatusAsync(string taskId, RobotTaskStatus status)
    {
        if (!_store.TryGetValue(taskId, out var task))
            return Task.FromResult(false);

        task.Status = status;
        if (status is RobotTaskStatus.Complete or RobotTaskStatus.Abort or RobotTaskStatus.Timeout)
            task.End = DateTime.Now;
        return Task.FromResult(true);
    }

    public Task<ConfirmTaskResult> ConfirmTaskAsync(string taskId)
    {
        if (!_store.TryGetValue(taskId, out var task))
            return Task.FromResult(ConfirmTaskResult.NotFound);
        if (task.Status is not (RobotTaskStatus.Complete or RobotTaskStatus.Abort or RobotTaskStatus.Timeout))
            return Task.FromResult(ConfirmTaskResult.WrongState);
        task.Confirmed = true;
        return Task.FromResult(ConfirmTaskResult.Success);
    }

    public Task<bool?> GetConfirmAsync(string taskId)
    {
        if (!_store.TryGetValue(taskId, out var task)) return Task.FromResult<bool?>(null);
        return Task.FromResult<bool?>(task.Confirmed);
    }

    public Task<Dictionary<string, RobotTask>> GetActiveTasksByRobotAsync()
    {
        var result = _store.Values
            .Where(t => t.Status is RobotTaskStatus.Idle or RobotTaskStatus.Process && !string.IsNullOrEmpty(t.Robot))
            .GroupBy(t => t.Robot!)
            .ToDictionary(g => g.Key, g => g.OrderByDescending(t => t.Status).First());
        return Task.FromResult(result);
    }
}

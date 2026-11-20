using Microsoft.AspNetCore.Mvc;
using Server.Models;
using Server.Services;

namespace Server.Controllers;

[ApiController]
[Route("api/robots")]
public class RobotController : ControllerBase
{
    private readonly RobotStateStore _store;
    private readonly RosBridgeTestService _rosBridge;
    private readonly ITaskService _taskService;

    private static readonly HashSet<string> HardwareOverrideStatuses = ["充電中", "緊急停止", "暫停"];
    private static string TaskTitle(TaskType taskType) => taskType switch
    {
        TaskType.WasteTransport => "廢棄物運送",
        TaskType.ClothesCollection => "衣物回收",
        TaskType.MedicationDelivery => "藥品配送",
        TaskType.SpecimenDelivery => "檢體配送",
        TaskType.WardService => "病房服務",
        _ => taskType.ToString(),
    };

    public RobotController(RobotStateStore store, RosBridgeTestService rosBridge, ITaskService taskService)
    {
        _store = store;
        _rosBridge = rosBridge;
        _taskService = taskService;
    }

    [HttpGet]
    public async Task<ActionResult<object>> GetAll()
    {
        var robots = _store.GetAll();
        var activeTasks = await _taskService.GetActiveTasksByRobotAsync();

        var enriched = robots.Select(r =>
        {
            if (!activeTasks.TryGetValue(r.Id, out var task))
                return r;

            if (HardwareOverrideStatuses.Contains(r.Status))
                return r;

            return new RobotDto
            {
                HasTelemetry = r.HasTelemetry,
                Id = r.Id,
                RosName = r.RosName,
                Name = r.Name,
                Model = r.Model,
                Manufacturer = r.Manufacturer,
                DescriptionPackage = r.DescriptionPackage,
                Capabilities = r.Capabilities,
                RobotType = r.RobotType,
                Status = !r.HasTelemetry || r.Status == "離線" ? "離線" : task.Status == RobotTaskStatus.Assigned ? "已指派待執行" : "執行任務中",
                Battery = r.Battery,
                CurrentTask = $"執行任務: {TaskTitle(task.TaskType)}",
                Location = r.Location,
                X = r.X,
                Y = r.Y,
                Yaw = r.Yaw,
                LevelName = r.LevelName,
                Signal = r.Signal,
                Uptime = r.Uptime,
                CompletedToday = r.CompletedToday,
                ConnectionIp = r.ConnectionIp,
                Firmware = r.Firmware,
                Mode = r.Mode,
                ModeText = !r.HasTelemetry || r.Status == "離線" ? "離線" : task.Status == RobotTaskStatus.Assigned ? "已指派待執行" : "執行任務中",
                LastUpdate = r.LastUpdate,
                CurrentTaskDetail = new RobotTaskDetailDto
                {
                    TaskNo = task.TaskCode,
                    Title = TaskTitle(task.TaskType),
                    Progress = r.CurrentTaskDetail.Progress > 0 ? r.CurrentTaskDetail.Progress : 0,
                    Step = r.CurrentTaskDetail.Step is not ("待命中" or "") ? r.CurrentTaskDetail.Step : "執行任務中",
                    StartedAt = r.CurrentTaskDetail.StartedAt,
                    Eta = r.CurrentTaskDetail.Eta,
                    Payload = r.CurrentTaskDetail.Payload,
                },
            };
        }).ToList();

        return new
        {
            connection = new
            {
                url = _store.RosBridgeUrl,
                status = _store.ConnectionStatus,
                failMessage = _store.FailMessage,
                retryCount = _store.RetryCount,
            },
            robots = enriched,
            pendingRobots = _store.GetPendingRobots(),
        };
    }

    [HttpPost("connect")]
    public ActionResult<object> Connect([FromBody] ConnectRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Url))
            return BadRequest(new { error = "URL 不可為空" });

        _rosBridge.Connect(request.Url);
        return new { success = true, url = request.Url };
    }

    [HttpPost("disconnect")]
    public ActionResult<object> Disconnect()
    {
        _rosBridge.Disconnect();
        return new { success = true };
    }

    [HttpPost("confirm")]
    public ActionResult<object> ConfirmRobot([FromBody] ConfirmRobotRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.RosName))
            return BadRequest(new { error = "rosName 不可為空" });

        var displayName = string.IsNullOrWhiteSpace(request.DisplayName) ? request.RosName : request.DisplayName;
        if (!_store.ConfirmRobot(request.RosName, displayName))
            return BadRequest(new { error = "目前只允許更新已註冊的七台機器人" });
        return new { success = true, rosName = request.RosName, displayName };
    }
}

public class ConnectRequest
{
    public string Url { get; set; } = string.Empty;
}

public class ConfirmRobotRequest
{
    public string RosName { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
}

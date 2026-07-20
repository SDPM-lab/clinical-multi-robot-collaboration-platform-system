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
                Id = r.Id,
                RosName = r.RosName,
                Name = r.Name,
                Model = r.Model,
                Status = "執行任務中",
                Battery = r.Battery,
                CurrentTask = $"執行任務: {task.Title}",
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
                ModeText = "執行任務中",
                LastUpdate = r.LastUpdate,
                CurrentTaskDetail = new RobotTaskDetailDto
                {
                    TaskNo = task.Id,
                    Title = task.Title,
                    Progress = r.CurrentTaskDetail.Progress > 0 ? r.CurrentTaskDetail.Progress : 0,
                    Step = r.CurrentTaskDetail.Step is not ("待命中" or "") ? r.CurrentTaskDetail.Step : "執行任務中",
                    StartedAt = task.Start?.ToString("HH:mm") ?? "—",
                    Eta = task.End?.ToString("HH:mm") ?? "—",
                    Payload = string.Join("、", task.Items),
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
        _store.ConfirmRobot(request.RosName, displayName);
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

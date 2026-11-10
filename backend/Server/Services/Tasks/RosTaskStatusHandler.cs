using System.Text.Json;
using Server.Models;

namespace Server.Services.Tasks;

// 將 RMF TaskSummary 轉成任務狀態；不從移動、閒置或任務 ID 消失推測完成。
public sealed class RosTaskStatusHandler(ITaskService taskService, RobotStateStore robots, ILogger<RosTaskStatusHandler> logger)
{
    public async Task HandleAsync(JsonElement message)
    {
        if (!message.TryGetProperty("task_id", out var id) || id.ValueKind != JsonValueKind.String ||
            !message.TryGetProperty("state", out var state) || state.ValueKind != JsonValueKind.Number || !state.TryGetInt32(out var code)) return;
        var taskId = id.GetString();
        if (string.IsNullOrWhiteSpace(taskId)) return;

        RobotTaskStatus? status = code switch
        {
            0 => null,
            1 => RobotTaskStatus.Running,
            2 => RobotTaskStatus.Completed,
            3 => RobotTaskStatus.Failed,
            4 => RobotTaskStatus.Cancelled,
            5 => null,
            _ => null,
        };
        if (status is null) return;


        var startedAt = status == RobotTaskStatus.Assigned
            ? null : ReadTime(message, "start_time");
        // TaskSummary 執行中的 end_time 是預估值，只在終止狀態採用。
        var finishedAt = status is RobotTaskStatus.Completed or RobotTaskStatus.Failed or RobotTaskStatus.Cancelled
            ? ReadTime(message, "end_time") : null;
        var rosName = message.TryGetProperty("robot_name", out var robot) && robot.ValueKind == JsonValueKind.String
            ? robot.GetString() : null;
        var robotId = string.IsNullOrWhiteSpace(rosName) ? null : robots.GetMapping(rosName)?.Id;
        if (!await taskService.UpdateTaskStatusAsync(taskId, status.Value, startedAt, finishedAt, robotId))
            logger.LogWarning("Ignored ROS task report: unknown task or invalid transition. TaskId={TaskId}, State={State}", taskId, code);
    }

    public async Task HandleDispatchAsync(JsonElement message)
    {
        if (!message.TryGetProperty("task_id", out var id) || id.ValueKind != JsonValueKind.String ||
            !message.TryGetProperty("status", out var state) || !state.TryGetInt32(out var status)) return;
        var taskId = id.GetString();
        if (string.IsNullOrWhiteSpace(taskId)) return;

        // DispatchState: DISPATCHED=3 才代表 fleet adapter 已確認；FAILED_TO_ASSIGN=4 是明確分配失敗。
        if (status is not (3 or 4)) return;
        string? robotId = null;
        if (status == 3)
        {
            if (!message.TryGetProperty("assignment", out var assignment) ||
                !assignment.TryGetProperty("is_assigned", out var isAssigned) || isAssigned.ValueKind != JsonValueKind.True ||
                !assignment.TryGetProperty("expected_robot_name", out var robot) || robot.ValueKind != JsonValueKind.String)
                return;
            var rosName = robot.GetString();
            if (string.IsNullOrWhiteSpace(rosName)) return;
            robotId = robots.GetMapping(rosName)?.Id ?? rosName;
        }
        if (!await taskService.UpdateTaskDispatchAsync(taskId, status == 3, robotId))
            logger.LogWarning("Ignored RMF dispatch report: unknown task or invalid transition. TaskId={TaskId}, Status={Status}", taskId, status);
    }

    private static DateTimeOffset? ReadTime(JsonElement message, string field)
    {
        if (!message.TryGetProperty(field, out var value) || value.ValueKind != JsonValueKind.Object ||
            !value.TryGetProperty("sec", out var seconds) || !seconds.TryGetInt64(out var sec) || sec <= 0) return null;
        var nanosec = value.TryGetProperty("nanosec", out var nanos) && nanos.TryGetInt32(out var ns) ? ns : 0;
        if (nanosec < 0 || nanosec >= 1_000_000_000) return null;
        try { return DateTimeOffset.FromUnixTimeSeconds(sec).AddTicks(nanosec / 100); }
        catch (ArgumentOutOfRangeException) { return null; }
    }
}

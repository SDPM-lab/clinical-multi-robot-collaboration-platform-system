namespace Server.Models;

public class RobotTask
{
    public string Id { get; set; } = string.Empty;
    public string TaskCode { get; set; } = string.Empty;
    public TaskType TaskType { get; set; }
    public string Source { get; set; } = string.Empty;
    public string Destination { get; set; } = string.Empty;
    public TaskPriority Priority { get; set; } = TaskPriority.Normal;
    public List<RobotCapability> RequiredCapabilities { get; set; } = [];
    public RobotTaskStatus Status { get; set; } = RobotTaskStatus.Pending;
    // 建立任務時指定的偏好機器人，尚未經派工服務確認。
    public string? RequestedRobotId { get; set; }
    public string? AssignedRobot { get; set; }
    // 僅限 Development 的派工流程；前端必須標示為模擬，不能冒充真實派工。
    public bool IsSimulated { get; internal set; }
    [System.Text.Json.Serialization.JsonIgnore]
    public DateTimeOffset? SimulationQueuedAt { get; internal set; }
    [System.Text.Json.Serialization.JsonIgnore]
    public string? SimulationRobotId { get; internal set; }
    // 使用者設定的預定開始時間。
    public DateTimeOffset? ScheduledAt { get; set; }
    // 確認機器人開始執行時記錄；尚未開始時為 null。
    public DateTimeOffset? StartedAt { get; set; }
    // 確認任務完成、失敗或取消時記錄；尚未結束時為 null。
    public DateTimeOffset? FinishedAt { get; set; }
    public string? Note { get; set; }
    [System.Text.Json.Serialization.JsonIgnore]
    public bool Dispatched { get; internal set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

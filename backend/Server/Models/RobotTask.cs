using System.Text.Json.Serialization;

namespace Server.Models;

public class RobotTask
{
    public string Id { get; set; } = string.Empty;
    public TaskType TaskType { get; set; }
    public string Source { get; set; } = string.Empty;
    public string Destination { get; set; } = string.Empty;
    public TaskPriority Priority { get; set; } = TaskPriority.Normal;
    public List<RobotCapability> RequiredCapabilities { get; set; } = [];
    public RobotTaskStatus Status { get; set; } = RobotTaskStatus.Pending;
    public string? AssignedRobot { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // =========================
    // 舊前端 / API 暫時使用
    // =========================

    public string Title { get; set; } = string.Empty;
    public List<string> Items { get; set; } = [];
    public DateTime? Start { get; set; }
    public DateTime? End { get; set; }
    public string? Note { get; set; }

    // Human-in-the-loop
    [JsonIgnore]
    public bool Confirmed { get; set; }
}
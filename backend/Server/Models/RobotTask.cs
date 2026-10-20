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
}

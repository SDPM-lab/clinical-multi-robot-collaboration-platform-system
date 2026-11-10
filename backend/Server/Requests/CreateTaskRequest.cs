using System.ComponentModel.DataAnnotations;
using Server.Models;

namespace Server.Requests;

public class CreateTaskRequest
{
    [Required]
    [EnumDataType(typeof(TaskType))]
    public TaskType TaskType { get; set; }

    [Required]
    public string Source { get; set; } = string.Empty;

    [Required]
    public string Destination { get; set; } = string.Empty;

    [Required]
    [EnumDataType(typeof(TaskPriority))]
    public TaskPriority Priority { get; set; } = TaskPriority.Normal;

    public string? RobotId { get; set; }
    [Required]
    public DateTimeOffset? ScheduledAt { get; set; }
    public string? Note { get; set; }
}

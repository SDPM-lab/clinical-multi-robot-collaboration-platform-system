using System.ComponentModel.DataAnnotations;
using Server.Models;

namespace Server.Requests;

public class CreateTaskRequest
{
    [Required]
    public TaskType TaskType { get; set; }

    [Required]
    public string Source { get; set; } = string.Empty;

    [Required]
    public string Destination { get; set; } = string.Empty;

    [Required]
    public TaskPriority Priority { get; set; } = TaskPriority.Normal;
}

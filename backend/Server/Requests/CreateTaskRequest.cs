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

    // 舊前端欄位暫時保留
    public string Title { get; set; } = string.Empty;
    public string? StartTime { get; set; }
    public List<string> Items { get; set; } = [];
    public string? Note { get; set; }
}
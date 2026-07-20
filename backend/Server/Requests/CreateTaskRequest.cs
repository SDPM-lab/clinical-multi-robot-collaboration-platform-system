using System.ComponentModel.DataAnnotations;

namespace Server.Requests;

public class CreateTaskRequest
{
    [Required]
    public string Title { get; set; } = string.Empty;

    public string? Robot { get; set; }

    [Required]
    public string Place { get; set; } = string.Empty;

    public string? StartTime { get; set; }

    [Required, MinLength(1), MaxLength(3)]
    public List<string> Items { get; set; } = [];

    public string? Note { get; set; }
}

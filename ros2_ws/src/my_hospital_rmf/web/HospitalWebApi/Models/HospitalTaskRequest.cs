namespace HospitalWebApi.Models;

public class HospitalTaskRequest
{
    public string Target { get; set; } = string.Empty;

    public int Priority { get; set; } = 1;

    public string TaskType { get; set; } = "go_to_place";

    public string? Note { get; set; }
}

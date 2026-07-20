namespace Server.Models;

public class RobotTask
{
    public string Id { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Place { get; set; } = string.Empty;
    public List<string> Items { get; set; } = [];
    public DateTime? Start { get; set; }
    public DateTime? End { get; set; }
    public string? Note { get; set; }
    public string? Robot { get; set; }
    public RobotTaskStatus Status { get; set; }
    [System.Text.Json.Serialization.JsonIgnore]
    public bool Confirmed { get; set; }
}

using System.ComponentModel.DataAnnotations;

namespace Server.Requests;

public class UpdateTaskScheduleRequest
{
    [Required]
    public DateTimeOffset? ScheduledAt { get; set; }
}

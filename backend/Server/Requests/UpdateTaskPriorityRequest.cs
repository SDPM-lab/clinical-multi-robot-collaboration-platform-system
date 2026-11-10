using System.ComponentModel.DataAnnotations;
using Server.Models;

namespace Server.Requests;

public class UpdateTaskPriorityRequest
{
    [Required]
    [EnumDataType(typeof(TaskPriority))]
    public TaskPriority? Priority { get; set; }
}

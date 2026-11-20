using Server.Models;
using Server.Requests;

namespace Server.Services;

public enum DeleteTaskResult { Success, NotFound, Forbidden }

public enum UpdateTaskScheduleResult { Success, NotFound, Forbidden }
public sealed record UpdateTaskScheduleOutcome(UpdateTaskScheduleResult Result, RobotTask? Replacement = null);
public enum CancelTaskResult { Success, NotFound, Forbidden }

public enum UpdateTaskPriorityResult { Success, NotFound, Forbidden }
public enum SimulatedArrivalResult { Success, NotFound, Forbidden }

public interface ITaskService
{
    Task<List<RobotTask>> GetTasksAsync();
    Task<Dictionary<string, RobotTask>> GetActiveTasksByRobotAsync();
    Task<RobotTask?> GetTaskByIdAsync(string taskId);
    Task<RobotTask> CreateTaskAsync(CreateTaskRequest request);
    Task<DeleteTaskResult> DeleteTaskAsync(string taskId);
    Task<CancelTaskResult> CancelPendingTaskAsync(string taskId);
    Task<UpdateTaskScheduleOutcome> UpdateTaskScheduleAsync(string taskId, UpdateTaskScheduleRequest request);
    Task<UpdateTaskPriorityResult> UpdateTaskPriorityAsync(string taskId, UpdateTaskPriorityRequest request);
    Task<bool> UpdateTaskDispatchAsync(string taskId, bool assigned, string? robotId = null);
    Task<bool> UpdateTaskStatusAsync(string taskId, RobotTaskStatus status, DateTimeOffset? startedAt = null, DateTimeOffset? finishedAt = null, string? robotId = null);
    Task<SimulatedArrivalResult> CompleteSimulatedArrivalAsync(string taskId, string robotId, string source, string destination);
}

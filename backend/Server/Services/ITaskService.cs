using Server.Models;
using Server.Requests;

namespace Server.Services;

public enum DeleteTaskResult { Success, NotFound, Forbidden }

public interface ITaskService
{
    Task<List<RobotTask>> GetTasksAsync();
    Task<RobotTask?> GetTaskByIdAsync(string taskId);
    Task CreateTaskAsync(CreateTaskRequest request);
    Task<DeleteTaskResult> DeleteTaskAsync(string taskId);
    Task<bool> UpdateTaskStatusAsync(string taskId, RobotTaskStatus status);
    Task<Dictionary<string, RobotTask>> GetActiveTasksByRobotAsync();
}

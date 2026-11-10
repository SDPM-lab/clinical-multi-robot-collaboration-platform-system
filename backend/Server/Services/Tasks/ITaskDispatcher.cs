using Server.Models;

namespace Server.Services.Tasks;

// TaskService 不決定使用哪一種模型或機器人，由派工整合層負責。
public interface ITaskDispatcher
{
    bool IsConfigured { get; }
    Task SendAsync(RobotTask task);
    Task ReleaseAssignmentAsync(RobotTask task);
}

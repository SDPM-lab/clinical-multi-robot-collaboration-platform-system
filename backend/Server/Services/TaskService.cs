using Server.Models;
using Server.Requests;
using Server.Services.Tasks;

namespace Server.Services;

public class TaskService : ITaskService
{
    // 保存任務儲存、ROS 通訊與日誌工具，供下方流程使用。
    private readonly TaskStore _store;
    private readonly ITaskDispatcher _dispatcher;
    private readonly ILogger<TaskService> _logger;
    internal bool IsExternalDispatcherConfigured => _dispatcher.IsConfigured;

    // 透過依賴注入取得此服務需要的工具。
    public TaskService(TaskStore store, ITaskDispatcher dispatcher, ILogger<TaskService> logger)
    {
        _store = store;
        _dispatcher = dispatcher;
        _logger = logger;
    }

    // 查詢目前儲存的所有任務。
    public Task<List<RobotTask>> GetTasksAsync()
    {
        return Task.FromResult(_store.GetAll());
    }

    // 依任務 ID 查詢單一任務，找不到時回傳 null。
    public Task<RobotTask?> GetTaskByIdAsync(string taskId)
    {
        _store.TryGet(taskId, out var task);

        return Task.FromResult(task);
    }

    // 依機器人分組，取得各機器人最新的已指派或執行中任務。
    public Task<Dictionary<string, RobotTask>> GetActiveTasksByRobotAsync()
    {
        var result = _store.GetAll()
            .Where(task => (task.Status is RobotTaskStatus.Assigned or RobotTaskStatus.Running)
                && !string.IsNullOrEmpty(task.AssignedRobot))
            .GroupBy(task => task.AssignedRobot!)
            .ToDictionary(
                group => group.Key,
                group => group.OrderByDescending(task => task.CreatedAt).First());

        return Task.FromResult(result);
    }

    // 確認預定時間有效後，建立並保存待處理任務。
    public Task<RobotTask> CreateTaskAsync(CreateTaskRequest request)
    {
        if (!Enum.IsDefined(request.TaskType))
            throw new ArgumentException("Invalid task type.");
        if (!Enum.IsDefined(request.Priority))
            throw new ArgumentException("Invalid task priority.");
        if (request.ScheduledAt is null || request.ScheduledAt <= DateTimeOffset.UtcNow)
            throw new ArgumentException("Scheduled time must be in the future.");

        var task = new RobotTask
        {
            Id = Guid.NewGuid().ToString(), // 使用 GUID 作為內部任務 ID，避免同時建立時重複。
            TaskCode = _store.NextTaskCode(),
            TaskType = request.TaskType,
            Source = request.Source,
            Destination = request.Destination,
            Priority = request.Priority,
            RequiredCapabilities = GetRequiredCapabilities(request.TaskType),
            Status = RobotTaskStatus.Pending,
            RequestedRobotId = request.RobotId,
            ScheduledAt = request.ScheduledAt,
            Note = request.Note,
            CreatedAt = DateTime.UtcNow,
        };

        _store.Add(task);
        return Task.FromResult(task);
    }

    // 待派工或已指派但未開始的任務可重新排程；建立新任務以重新選擇機器人。
    public async Task<UpdateTaskScheduleOutcome> UpdateTaskScheduleAsync(
        string taskId, UpdateTaskScheduleRequest request)
    {
        if (request.ScheduledAt is null || request.ScheduledAt <= DateTimeOffset.UtcNow)
            throw new ArgumentException("Scheduled time must be in the future.");

        // await 表示等待時不需要讓執行緒忙碌地反覆檢查；等拿到鎖之後才繼續
        await _store.DispatchGate.WaitAsync(); // 非同步等待取得，避免同一時間剛好有另一個流程同時派送或修改任務
        try
        {
            if (!_store.TryGet(taskId, out var task))
                return new(UpdateTaskScheduleResult.NotFound);
            if (task.StartedAt.HasValue ||
                !(task.Status == RobotTaskStatus.Pending || task.Status == RobotTaskStatus.Assigned))
                return new(UpdateTaskScheduleResult.Forbidden);
            // 接上外部服務後，必須先確認撤回舊指派；失敗時不建立新任務。
            if (task.Dispatched || task.Status == RobotTaskStatus.Assigned)
                await _dispatcher.ReleaseAssignmentAsync(task);
            // 新 ID 確保舊任務回報不會更新到新任務。
            var replacement = await CreateTaskAsync(new CreateTaskRequest
            {
                TaskType = task.TaskType, Source = task.Source, Destination = task.Destination,
                Priority = task.Priority, ScheduledAt = request.ScheduledAt, Note = task.Note,
                RobotId = null
            });
            _store.Remove(taskId);
            return new(UpdateTaskScheduleResult.Success, replacement);
        }
        finally
        {
            _store.DispatchGate.Release(); // 歸還鎖，讓其他等待中的操作可以繼續
        }
    }

    // 只修改尚未派送的待處理任務，避免與 ROS 已接收的優先級不一致。
    public async Task<UpdateTaskPriorityResult> UpdateTaskPriorityAsync(string taskId, UpdateTaskPriorityRequest request)
    {
        if (request.Priority is null || !Enum.IsDefined(request.Priority.Value))
            throw new ArgumentException("Invalid task priority.");

        await _store.DispatchGate.WaitAsync();
        try
        {
            if (!_store.TryGet(taskId, out var task)) return UpdateTaskPriorityResult.NotFound;
            if (task.Status != RobotTaskStatus.Pending || task.Dispatched) return UpdateTaskPriorityResult.Forbidden;
            task.Priority = request.Priority.Value;
            return UpdateTaskPriorityResult.Success;
        }
        finally { _store.DispatchGate.Release(); }
    }

    // 只允許刪除尚未派送的待處理任務。
    public async Task<DeleteTaskResult> DeleteTaskAsync(string taskId)
    {
        await _store.DispatchGate.WaitAsync();
        try
        {
            if (!_store.TryGet(taskId, out var task))
                return DeleteTaskResult.NotFound;
            if (task.Status != RobotTaskStatus.Pending || task.Dispatched)
                return DeleteTaskResult.Forbidden;
            _store.Remove(taskId);
            return DeleteTaskResult.Success;
        }
        finally
        {
            _store.DispatchGate.Release();
        }
    }

    // 使用者只能取消尚未送出的 Pending 任務；外部執行回報不走此操作。
    public async Task<CancelTaskResult> CancelPendingTaskAsync(string taskId)
    {
        await _store.DispatchGate.WaitAsync();
        try
        {
            if (!_store.TryGet(taskId, out var task)) return CancelTaskResult.NotFound;
            if (task.Status != RobotTaskStatus.Pending || task.Dispatched) return CancelTaskResult.Forbidden;
            task.Status = RobotTaskStatus.Cancelled;
            task.FinishedAt = DateTimeOffset.UtcNow;
            return CancelTaskResult.Success;
        }
        finally { _store.DispatchGate.Release(); }
    }

    // 由派工服務的明確結果確認分配，不由 ROS 移動狀態推測。
    public async Task<bool> UpdateTaskDispatchAsync(string taskId, bool assigned, string? robotId = null)
    {
        await _store.DispatchGate.WaitAsync();
        try
        {
            if (!_store.TryGet(taskId, out var task) || !task.Dispatched)
                return false;
            // 執行回報可能比派工回報先到；晚到的確認只補機器人，不讓狀態倒退。
            if (assigned && task.Status is (RobotTaskStatus.Assigned or RobotTaskStatus.Running))
            {
                if (!string.IsNullOrWhiteSpace(robotId)) task.AssignedRobot = robotId;
                return true;
            }
            if (task.Status != RobotTaskStatus.Pending) return false;
            if (assigned)
            {
                if (string.IsNullOrWhiteSpace(robotId)) return false;
                task.AssignedRobot = robotId;
                task.Status = RobotTaskStatus.Assigned;
            }
            else
            {
                task.Status = RobotTaskStatus.Failed;
                task.FinishedAt ??= DateTimeOffset.UtcNow;
            }
            return true;
        }
        finally { _store.DispatchGate.Release(); }
    }

    // 依任務 ID 更新狀態，並避免與派送流程同時修改。
    public async Task<bool> UpdateTaskStatusAsync(
        string taskId, RobotTaskStatus status,
        DateTimeOffset? startedAt = null, DateTimeOffset? finishedAt = null,
        string? robotId = null)
    {
        await _store.DispatchGate.WaitAsync();
        try
        {
            if (!_store.TryGet(taskId, out var task))
                return false;
            if (!Enum.IsDefined(status)) return false;
            // 終止狀態不接受舊回報覆寫，重複通知也不重新計時。
            if (IsTerminal(task.Status)) return task.Status == status;
            if (task.Status == RobotTaskStatus.Running && status is RobotTaskStatus.Pending or RobotTaskStatus.Assigned)
                return false;
            if (task.Status == RobotTaskStatus.Assigned && status == RobotTaskStatus.Pending)
                return false;
            if (task.Dispatched && status == RobotTaskStatus.Pending) return false;

            var now = DateTimeOffset.UtcNow;
            var actualStart = task.StartedAt ?? startedAt;
            if (status == RobotTaskStatus.Running) actualStart ??= now;
            DateTimeOffset? actualFinish = IsTerminal(status) ? finishedAt ?? now : null;
            if (actualStart.HasValue && actualFinish.HasValue && actualFinish < actualStart) return false;

            task.StartedAt ??= actualStart;
            if (IsTerminal(status)) task.FinishedAt ??= actualFinish;
            if (!string.IsNullOrWhiteSpace(robotId)) task.AssignedRobot = robotId;
            if (status is RobotTaskStatus.Assigned or RobotTaskStatus.Running)
                task.Dispatched = true;
            task.Status = status;
            return true;
        }
        finally
        {
            _store.DispatchGate.Release();
        }
    }

    // Development 畫面模擬抵達：只接受目前執行中的模擬任務，並核對機器人與原任務起終點。
    public async Task<SimulatedArrivalResult> CompleteSimulatedArrivalAsync(string taskId, string robotId, string source, string destination)
    {
        await _store.DispatchGate.WaitAsync();
        try
        {
            if (!_store.TryGet(taskId, out var task)) return SimulatedArrivalResult.NotFound;
            if (!task.IsSimulated || task.Status != RobotTaskStatus.Running ||
                task.AssignedRobot != robotId || task.Source != source || task.Destination != destination)
                return SimulatedArrivalResult.Forbidden;
            task.Status = RobotTaskStatus.Completed;
            task.FinishedAt = DateTimeOffset.UtcNow;
            return SimulatedArrivalResult.Success;
        }
        finally { _store.DispatchGate.Release(); }
    }

    // 建立後即提交派工；預定時間一併傳給派工服務，避免提早執行。
    internal async Task DispatchDueTasksAsync(CancellationToken cancellationToken)
    {
        if (!_dispatcher.IsConfigured) return;
        await _store.DispatchGate.WaitAsync(cancellationToken);
        try
        {
            foreach (var task in _store.GetAll().Where(task =>
                task.Status == RobotTaskStatus.Pending && !task.Dispatched))
            {
                cancellationToken.ThrowIfCancellationRequested();
                // 送出前先封鎖重複派送；HTTP 成功仍須等待派工服務分配結果。
                task.Dispatched = true;
                try
                {
                    await _dispatcher.SendAsync(task);
                }
                catch (ArgumentException ex)
                {
                    // HTTP 明確拒收；沒有 ROS 執行開始時間。
                    task.Status = RobotTaskStatus.Failed;
                    task.FinishedAt ??= DateTimeOffset.UtcNow;
                    _logger.LogError(ex, "Scheduled task {TaskId} was rejected by the bridge", task.Id);
                }
                catch (InvalidOperationException ex)
                {
                    // 網路錯誤或逾時可能已送達，保留等待確認且不自動重送。
                    _logger.LogError(ex, "Scheduled task {TaskId} delivery is unconfirmed", task.Id);
                }
            }
        }
        finally
        {
            _store.DispatchGate.Release(); // 歸還閘門
        }
    }

    // 僅由 Development worker 呼叫。模擬只改任務狀態，不產生假的 ROS 定位或完成回報。
    internal async Task SimulateDueTasksAsync(RobotStateStore robots, CancellationToken cancellationToken)
    {
        await _store.DispatchGate.WaitAsync(cancellationToken);
        try
        {
            var now = DateTimeOffset.UtcNow;
            var registered = robots.GetRegistrations().OrderBy(robot => robot.RosName, StringComparer.Ordinal).ToList();
            var occupied = _store.GetAll().Where(task => task.Status is RobotTaskStatus.Assigned or RobotTaskStatus.Running)
                .Select(task => task.AssignedRobot ?? task.SimulationRobotId).Where(id => id is not null).ToHashSet();
            foreach (var task in _store.GetAll().Where(task => task.IsSimulated && task.Status == RobotTaskStatus.Assigned
                && task.ScheduledAt <= now))
            {
                task.Status = RobotTaskStatus.Running;
                task.StartedAt ??= now;
            }
            foreach (var task in _store.GetAll().Where(task => task.Status == RobotTaskStatus.Pending && !task.Dispatched)
                .OrderBy(task => task.ScheduledAt))
            {
                var robot = registered.FirstOrDefault(candidate => !occupied.Contains(candidate.Id) &&
                    (candidate.RobotType switch
                    {
                        "clean" => task.TaskType is TaskType.WasteTransport or TaskType.ClothesCollection,
                        "medical" => task.TaskType is TaskType.MedicationDelivery or TaskType.SpecimenDelivery,
                        "ward" => task.TaskType is TaskType.MedicationDelivery or TaskType.WardService,
                        _ => false,
                    }));
                if (robot is null) continue;
                task.Status = RobotTaskStatus.Assigned;
                task.AssignedRobot = robot.Id;
                task.Dispatched = true;
                task.IsSimulated = true;
                task.SimulationRobotId = robot.Id;
                task.SimulationQueuedAt = now;
                occupied.Add(robot.Id);
            }
        }
        finally { _store.DispatchGate.Release(); }
    }

    // 終止狀態代表任務已結束，不能由延遲抵達的回報重新啟動。
    private static bool IsTerminal(RobotTaskStatus status)
        => status is RobotTaskStatus.Completed or RobotTaskStatus.Failed or RobotTaskStatus.Cancelled;

    // 依任務類型決定執行時需要的機器人能力。
    private static List<RobotCapability> GetRequiredCapabilities(TaskType taskType)
    {
        return taskType switch
        {
            TaskType.WasteTransport => [RobotCapability.WasteTransport],
            TaskType.ClothesCollection => [RobotCapability.ClothesCollection],
            TaskType.MedicationDelivery => [RobotCapability.MedicationDelivery],
            TaskType.SpecimenDelivery => [RobotCapability.SpecimenDelivery],
            TaskType.WardService => [RobotCapability.WardService],
            _ => []
        };
    }
}

using System.Collections.Concurrent;
using System.Diagnostics.CodeAnalysis;
using Server.Models;

namespace Server.Services.Tasks;

// 在 Program.cs 註冊為單例，供任務服務與背景排程共用。
// 任務與編號只保存在記憶體，伺服器停止後不會保留。
public sealed class TaskStore : IDisposable  // sealed：其他類別不能繼承 TaskStore
{
    // 以內部任務 ID 為索引，儲存 RobotTask 任務物件。
    private readonly ConcurrentDictionary<string, RobotTask> _tasks = new(); //readonly：這個欄位初始化後不能改指向另一個字典，但可以修改字典裡的內容

    // 記錄產生易讀任務代碼所使用的流水號。
    private long _taskSequence;

    // TaskService 透過此鎖，避免派送時同時修改或刪除任務。
    internal SemaphoreSlim DispatchGate { get; } = new(1, 1);

    // 取得目前所有任務物件的清單。
    public List<RobotTask> GetAll()
    {
        return _tasks.Values.ToList();
    }

    // 查詢 ID 是否存在，並透過 out 參數提供對應的任務物件。
    public bool TryGet(string id, [NotNullWhen(true)] out RobotTask? task)
    {
        return _tasks.TryGetValue(id, out task);
    }

    // 使用任務的內部 ID 作為字典索引，保存任務物件。
    public void Add(RobotTask task)
    {
        _tasks[task.Id] = task;
    }

    // 依任務 ID 移除資料；移除成功回傳 true，找不到該 ID 則回傳 false。
    public bool Remove(string id)
    {
        return _tasks.TryRemove(id, out _);
    }

    // 使用不可分割的計數操作產生 T0001 等代碼，避免同時建立時編號重複。
    public string NextTaskCode()
    {
        return $"T{Interlocked.Increment(ref _taskSequence):D4}";
    }

    // 應用程式釋放此儲存服務時，一併釋放同步鎖資源。
    public void Dispose()
    {
        DispatchGate.Dispose();
    }
}

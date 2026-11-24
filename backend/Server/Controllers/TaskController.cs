using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Server.Models;
using Server.Requests;
using Server.Services;

namespace Server.Controllers;

public sealed record SimulatedArrivalRequest(string RobotId, string Source, string Destination);

[ApiController]
[Route("api/v1/task")]
public class TaskController : ControllerBase
{
    private readonly ITaskService _taskService;
    private readonly IWebHostEnvironment _environment;

    // 注入任務服務，將 API 請求交給服務層處理。
    public TaskController(ITaskService taskService, IWebHostEnvironment environment)
    {
        _taskService = taskService;
        _environment = environment;
    }

    // 只供 Development 的畫面路線模擬回報；正式任務須由派工／機器人回報完成。
    [HttpPost("{task_id}/simulation/arrive")]
    public async Task<IActionResult> CompleteSimulatedArrival(string task_id, [FromBody] SimulatedArrivalRequest request)
    {
        if (!_environment.IsDevelopment()) return NotFound();
        if (string.IsNullOrWhiteSpace(request.RobotId) || string.IsNullOrWhiteSpace(request.Source) ||
            string.IsNullOrWhiteSpace(request.Destination)) return BadRequest();
        return await _taskService.CompleteSimulatedArrivalAsync(task_id, request.RobotId, request.Source, request.Destination) switch
        {
            SimulatedArrivalResult.Success => NoContent(),
            SimulatedArrivalResult.NotFound => NotFound(),
            _ => Conflict("模擬任務尚未抵達，或任務／機器人／起終點不相符。"),
        };
    }

    // 查詢所有任務，供前端顯示任務清單。
    [HttpGet]
    public async Task<ActionResult<List<RobotTask>>> GetTasks()
        => Ok(await _taskService.GetTasksAsync());

    // 依任務 ID 查詢單筆資料，找不到時回傳 404。
    [HttpGet("{task_id}")]
    public async Task<ActionResult<RobotTask>> GetTask(string task_id)
    {
        var task = await _taskService.GetTaskByIdAsync(task_id);
        if (task is null)
            return NotFound("查無此任務");
        return Ok(task);
    }

    // 接收建立任務資料，成功時回傳 201、任務內容及查詢網址。
    [HttpPost]
    // IActionResult 是 ASP.NET Core 提供的型別，代表各種 HTTP 回應，例如 201、400 或 404
    public async Task<IActionResult> CreateTask([FromBody] CreateTaskRequest request)
    {
        try
        {
            if (!Server.Services.Tasks.TaskProfileLocations.IsAllowed(request.TaskType, request.Source, request.Destination))
                return BadRequest("Source and destination are not allowed for this task type.");
            var task = await _taskService.CreateTaskAsync(request);
            // 建立並回傳 HTTP 201 Created 回應，表示任務已成功建立
            return CreatedAtAction(nameof(GetTask), new { task_id = task.Id }, task);
        }
        catch (ArgumentException ex)
        {
            return BadRequest($"Invalid request: {ex.Message}");
        }
        catch (InvalidOperationException ex)
        {
            return StatusCode(503, $"任務派送服務目前無法使用：{ex.Message}");
        }
    }

    // 接收新的排程時間，由服務判斷是否允許修改。
    [HttpPatch("{task_id}/schedule")]
    public async Task<IActionResult> UpdateTaskSchedule(string task_id, [FromBody] UpdateTaskScheduleRequest request)
    {
        try
        {
            var result = await _taskService.UpdateTaskScheduleAsync(task_id, request);
            return result.Result switch
            {
                UpdateTaskScheduleResult.Success => CreatedAtAction(nameof(GetTask), new { task_id = result.Replacement!.Id }, result.Replacement),
                UpdateTaskScheduleResult.Forbidden => StatusCode(403, "任務已開始執行，不能更改時間。"),
                _ => NotFound("查無此任務"),
            };
        }
        catch (InvalidOperationException)
        {
            return StatusCode(503, new
            {
                code = "reschedule_dispatch_cancellation_unsupported",
                detail = "外部派工服務尚未支援撤回舊指派，原任務已保留，暫時無法重新排程。",
            });
        }
        catch (ArgumentException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    // 修改尚未派送任務的優先級。
    [HttpPatch("{task_id}/priority")]
    public async Task<IActionResult> UpdateTaskPriority(string task_id, [FromBody] UpdateTaskPriorityRequest request)
    {
        try
        {
            var result = await _taskService.UpdateTaskPriorityAsync(task_id, request);
            return result switch
            {
                UpdateTaskPriorityResult.Success => NoContent(),
                UpdateTaskPriorityResult.Forbidden => StatusCode(403, "Task has already been processed; priority cannot be changed."),
                _ => NotFound("Task not found."),
            };
        }
        catch (ArgumentException ex) { return BadRequest(ex.Message); }
    }

    // 刪除指定任務，依服務結果回傳成功、禁止或找不到。
    [HttpDelete("{task_id}")]
    public async Task<IActionResult> DeleteTask(string task_id)
    {
        var result = await _taskService.DeleteTaskAsync(task_id);
        return result switch
        {
            DeleteTaskResult.Success => NoContent(),
            DeleteTaskResult.Forbidden => StatusCode(403, "任務已被處理無法刪除"),
            _ => NotFound("查無此任務"),
        };
    }

    // 將指定任務狀態更新為已取消。
    [HttpPatch("{task_id}/abort")]
    public async Task<IActionResult> AbortTask(string task_id)
    {
        return await _taskService.CancelPendingTaskAsync(task_id) switch
        {
            CancelTaskResult.Success => Ok(),
            CancelTaskResult.Forbidden => Conflict("任務已送出或已指派，不能取消。"),
            _ => NotFound("查無此任務")
        };
    }

    // 透過 SSE 持續傳送既有任務的狀態變更。
    // SSE（Server-Sent Events）是一種讓伺服器透過 HTTP 連線，
    // 持續把事件推送給瀏覽器的方式。這段程式會每秒檢查任務狀態，發現變更時就傳送事件。
    [HttpGet("event/trace")]
    public async Task TraceEvents(CancellationToken cancellationToken)
    {
        Response.ContentType = "text/event-stream";
        Response.Headers.CacheControl = "no-cache";

        var snapshot = (await _taskService.GetTasksAsync())
            .ToDictionary(t => t.Id, t => t.Status);

        while (!cancellationToken.IsCancellationRequested)
        {
            await Task.Delay(1000, cancellationToken);

            var current = (await _taskService.GetTasksAsync())
                .ToDictionary(t => t.Id, t => t.Status);

            var changes = current
                .Where(kv => snapshot.TryGetValue(kv.Key, out var old) && old != kv.Value)
                .Select(kv => new
                {
                    id = kv.Key,
                    old = snapshot[kv.Key].ToString().ToLower(),
                    @new = kv.Value.ToString().ToLower()
                })
                .ToList();

            if (changes.Count > 0)
            {
                var json = JsonSerializer.Serialize(changes);
                await Response.WriteAsync($"data: {json}\n\n", cancellationToken);
                await Response.Body.FlushAsync(cancellationToken);
            }

            snapshot = current;
        }
    }
}

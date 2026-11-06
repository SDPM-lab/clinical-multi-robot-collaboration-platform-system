using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Server.Models;
using Server.Requests;
using Server.Services;

namespace Server.Controllers;

[ApiController]
[Route("api/v1/task")]
public class TaskController : ControllerBase
{
    private readonly ITaskService _taskService;

    public TaskController(ITaskService taskService)
    {
        _taskService = taskService;
    }

    [HttpPost]
    public async Task<IActionResult> CreateTask([FromBody] CreateTaskRequest request)
    {
        try
        {
            var task = await _taskService.CreateTaskAsync(request);
            return CreatedAtAction(nameof(GetTask), new { task_id = task.Id }, task);
        }
        catch (ArgumentException ex)
        {
            return BadRequest($"Invalid request: {ex.Message}");
        }
        catch (InvalidOperationException ex)
        {
            return StatusCode(
                503,
                $"任務派送服務目前無法使用：{ex.Message}"
            );
        }
    }

    [HttpGet]
    public async Task<ActionResult<List<RobotTask>>> GetTasks()
        => Ok(await _taskService.GetTasksAsync());

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
                    id   = kv.Key,
                    old  = snapshot[kv.Key].ToString().ToLower(),
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

    [HttpGet("{task_id}")]
    public async Task<ActionResult<RobotTask>> GetTask(string task_id)
    {
        var task = await _taskService.GetTaskByIdAsync(task_id);
        if (task is null)
            return NotFound("查無此任務");
        return Ok(task);
    }

    [HttpDelete("{task_id}")]
    public async Task<IActionResult> DeleteTask(string task_id)
    {
        var result = await _taskService.DeleteTaskAsync(task_id);
        return result switch
        {
            DeleteTaskResult.Success   => NoContent(),
            DeleteTaskResult.Forbidden => StatusCode(403, "任務已被處理無法刪除"),
            _                          => NotFound("查無此任務"),
        };
    }

    [HttpPatch("{task_id}/schedule")]
    public async Task<IActionResult> UpdateTaskSchedule(string task_id, [FromBody] UpdateTaskScheduleRequest request)
    {
        try
        {
            var result = await _taskService.UpdateTaskScheduleAsync(task_id, request);
            return result switch
            {
                UpdateTaskScheduleResult.Success => NoContent(),
                UpdateTaskScheduleResult.Forbidden => StatusCode(403, "任務已被處理無法修改排程"),
                _ => NotFound("查無此任務"),
            };
        }
        catch (ArgumentException ex) { return BadRequest(ex.Message); }
    }

    [HttpPatch("{task_id}/abort")]
    public async Task<IActionResult> AbortTask(string task_id)
    {
        var found = await _taskService.UpdateTaskStatusAsync(task_id, RobotTaskStatus.Cancelled);
        return found ? Ok() : NotFound("查無此任務");
    }
}

using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using HospitalWebApi.Models;

namespace HospitalWebApi.Controllers;

[ApiController]
[Route("api/[controller]")]
public class TasksController : ControllerBase
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly IConfiguration _configuration;
    private readonly ILogger<TasksController> _logger;

    public TasksController(
        IHttpClientFactory httpClientFactory,
        IConfiguration configuration,
        ILogger<TasksController> logger)
    {
        _httpClientFactory = httpClientFactory;
        _configuration = configuration;
        _logger = logger;
    }

    [HttpPost]
    public async Task<IActionResult> CreateTask([FromBody] HospitalTaskRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Target))
        {
            return BadRequest(new HospitalTaskResponse
            {
                Success = false,
                Message = "Target is required"
            });
        }

        if (request.Priority <= 0)
        {
            return BadRequest(new HospitalTaskResponse
            {
                Success = false,
                Message = "Priority must be greater than 0"
            });
        }

        if (request.TaskType != "go_to_place")
        {
            return BadRequest(new HospitalTaskResponse
            {
                Success = false,
                Message = "Only taskType='go_to_place' is supported now"
            });
        }

        var bridgeBaseUrl = _configuration["RosBridge:BaseUrl"]
            ?? "http://localhost:5050";

        var bridgeUrl = $"{bridgeBaseUrl}/api/hospital/tasks";

        var payload = new
        {
            target = request.Target,
            priority = request.Priority,
            task_type = request.TaskType,
            note = request.Note
        };

        var json = JsonSerializer.Serialize(payload);

        _logger.LogInformation("Forwarding hospital task to ROS bridge: {Json}", json);

        var client = _httpClientFactory.CreateClient();

        try
        {
            var content = new StringContent(
                json,
                Encoding.UTF8,
                "application/json"
            );

            var response = await client.PostAsync(bridgeUrl, content);
            var responseBody = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError(
                    "ROS bridge returned error. Status={Status}, Body={Body}",
                    response.StatusCode,
                    responseBody
                );

                return StatusCode(502, new HospitalTaskResponse
                {
                    Success = false,
                    Message = "ROS bridge request failed",
                    Data = responseBody
                });
            }

            return Ok(new HospitalTaskResponse
            {
                Success = true,
                Message = "Task forwarded to ROS bridge",
                Data = JsonSerializer.Deserialize<object>(responseBody)
            });
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "Failed to connect to ROS bridge");

            return StatusCode(503, new HospitalTaskResponse
            {
                Success = false,
                Message = "Cannot connect to ROS bridge. Please check hospital_ros_api_bridge.py is running."
            });
        }
    }

    [HttpGet("health")]
    public IActionResult Health()
    {
        return Ok(new
        {
            status = "ok",
            service = "HospitalWebApi"
        });
    }
}

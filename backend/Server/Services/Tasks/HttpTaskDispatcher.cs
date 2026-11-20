using System.Text;
using System.Text.Json;
using Server.Models;

namespace Server.Services.Tasks;

// 可設定的派工 HTTP 轉接器；不呼叫 Open-RMF 拍賣或派工 API。
// 暫沿用既有傳輸格式，模型契約確認後只需調整此整合層。
public sealed class HttpTaskDispatcher(
    IHttpClientFactory httpClientFactory,
    IConfiguration configuration,
    ILogger<HttpTaskDispatcher> logger) : ITaskDispatcher
{
    private readonly IHttpClientFactory _httpClientFactory = httpClientFactory;
    private readonly IConfiguration _configuration = configuration;
    private readonly ILogger<HttpTaskDispatcher> _logger = logger;

    public bool IsConfigured => Uri.TryCreate(_configuration["TaskDispatch:Endpoint"], UriKind.Absolute, out var uri)
        && uri.Scheme is "http" or "https";

    public Task ReleaseAssignmentAsync(RobotTask task)
    {
        // 未接外部模型時只有平台本地指派；外部撤回協定待模型契約確定後實作。
        // 已設定外部服務時不能假裝撤回成功，否則舊機器人可能繼續執行。
        if (IsConfigured) throw new InvalidOperationException("Assignment withdrawal must be integrated before rescheduling an externally assigned task.");
        return Task.CompletedTask;
    }

    public async Task SendAsync(RobotTask task)
    {
        if (!IsConfigured) throw new InvalidOperationException("Task dispatch endpoint is not configured.");
        var bridgeUrl = _configuration["TaskDispatch:Endpoint"]!;

        var payload = new
        {
            task_id = task.Id,
            task_type = ToSnakeCase(task.TaskType),
            source = task.Source,
            destination = task.Destination,
            priority = (int)task.Priority,
            required_capabilities = task.RequiredCapabilities.Select(ToSnakeCase).ToList(),
            created_at = new DateTimeOffset(task.CreatedAt).ToUnixTimeMilliseconds() / 1000.0,
            scheduled_at = task.ScheduledAt?.ToUnixTimeMilliseconds() / 1000.0
        };

        var json = JsonSerializer.Serialize(payload);

        _logger.LogInformation("Forwarding task to task dispatcher: {Json}", json);

        var client = _httpClientFactory.CreateClient();

        try
        {
            using var content = new StringContent(json, Encoding.UTF8, "application/json");
            using var response = await client.PostAsync(bridgeUrl, content);
            var responseBody = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError(
                    "task dispatcher request failed. Status={Status}, Body={Body}",
                    response.StatusCode, responseBody);

                var statusCode = (int)response.StatusCode;

                if (statusCode >= 400 && statusCode < 500)
                {
                    throw new ArgumentException($"task dispatcher rejected task: {statusCode} {responseBody}");
                }

                throw new InvalidOperationException($"task dispatcher unavailable: {statusCode} {responseBody}");
            }

            _logger.LogInformation("task dispatcher accepted task. Body={Body}", responseBody);
        }
        catch (ArgumentException)
        {
            throw;
        }
        catch (InvalidOperationException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to forward task to task dispatcher");

            throw new InvalidOperationException("Failed to connect to task dispatcher", ex);
        }
    }

    private static string ToSnakeCase(TaskType taskType)
    {
        return taskType switch
        {
            TaskType.WasteTransport => "waste_transport",
            TaskType.ClothesCollection => "clothes_collection",
            TaskType.MedicationDelivery => "medication_delivery",
            TaskType.SpecimenDelivery => "specimen_delivery",
            TaskType.WardService => "ward_service",
            _ => throw new ArgumentOutOfRangeException(nameof(taskType))
        };
    }

    private static string ToSnakeCase(RobotCapability capability)
    {
        return capability switch
        {
            RobotCapability.WasteTransport => "waste_transport",
            RobotCapability.ClothesCollection => "clothes_collection",
            RobotCapability.MedicationDelivery => "medication_delivery",
            RobotCapability.SpecimenDelivery => "specimen_delivery",
            RobotCapability.WardService => "ward_service",
            _ => throw new ArgumentOutOfRangeException(nameof(capability))
        };
    }
}

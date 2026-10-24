using System.Text;
using System.Text.Json;
using Server.Models;

namespace Server.Services.Tasks;

// Encapsulates the ROS bridge HTTP contract and payload conversion.
public sealed class RosTaskClient(
    IHttpClientFactory httpClientFactory,
    IConfiguration configuration,
    ILogger<RosTaskClient> logger)
{
    private readonly IHttpClientFactory _httpClientFactory = httpClientFactory;
    private readonly IConfiguration _configuration = configuration;
    private readonly ILogger<RosTaskClient> _logger = logger;

    public async Task SendAsync(RobotTask task)
    {
        var bridgeBaseUrl =
            _configuration["RosBridge:BaseUrl"]
            ?? "http://localhost:5050";

        var bridgeUrl =
            $"{bridgeBaseUrl}/api/hospital/tasks";

        var payload = new
        {
            task_id = task.Id,

            task_type =
                ToSnakeCase(task.TaskType),

            source = task.Source,

            destination = task.Destination,

            priority = (int)task.Priority,

            required_capabilities =
                task.RequiredCapabilities
                    .Select(ToSnakeCase)
                    .ToList(),

            created_at =
                new DateTimeOffset(
                    task.CreatedAt
                ).ToUnixTimeMilliseconds()
                / 1000.0
        };

        var json = JsonSerializer.Serialize(payload);

        _logger.LogInformation(
            "Forwarding task to ROS bridge: {Json}",
            json
        );

        var client =
            _httpClientFactory.CreateClient();

        try
        {
            using var content =
                new StringContent(
                    json,
                    Encoding.UTF8,
                    "application/json"
                );

            using var response =
                await client.PostAsync(
                    bridgeUrl,
                    content
                );

            var responseBody =
                await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError(
                    "ROS bridge request failed. Status={Status}, Body={Body}",
                    response.StatusCode,
                    responseBody
                );

                var statusCode = (int)response.StatusCode;

                if (statusCode >= 400 && statusCode < 500)
                {
                    throw new ArgumentException(
                        $"ROS bridge rejected task: {statusCode} {responseBody}"
                    );
                }

                throw new InvalidOperationException(
                    $"ROS bridge unavailable: {statusCode} {responseBody}"
                );
            }

            _logger.LogInformation(
                "ROS bridge accepted task. Body={Body}",
                responseBody
            );
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
            _logger.LogError(
                ex,
                "Failed to forward task to ROS bridge"
            );

            throw new InvalidOperationException(
                "Failed to connect to ROS bridge",
                ex
            );
        }
    }

    private static string ToSnakeCase(TaskType taskType)
    {
        return taskType switch
        {
            TaskType.MedicineDelivery => "medicine_delivery",
            TaskType.SpecimenDelivery => "specimen_delivery",
            TaskType.GeneralDelivery => "general_delivery",
            TaskType.WasteCollection => "waste_collection",
            _ => "general_delivery"
        };
    }

    private static string ToSnakeCase(RobotCapability capability)
    {
        return capability switch
        {
            RobotCapability.Navigation => "navigation",
            RobotCapability.GeneralDelivery => "general_delivery",
            RobotCapability.MedicineDelivery => "medicine_delivery",
            RobotCapability.SpecimenDelivery => "specimen_delivery",
            RobotCapability.Manipulation => "manipulation",
            _ => capability.ToString().ToLowerInvariant()
        };
    }

}

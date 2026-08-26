using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Server.Services;

namespace Server.Tests.Unit.Services;

public class TaskServiceTests
{
    private static TaskService CreateService()
    {
        var httpClientFactory = new TestHttpClientFactory();

        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["RosBridge:BaseUrl"] = "http://localhost:5050"
            })
            .Build();

        var logger = NullLogger<TaskService>.Instance;

        return new TaskService(
            httpClientFactory,
            configuration,
            logger
        );
    }

    private sealed class TestHttpClientFactory : IHttpClientFactory
    {
        public HttpClient CreateClient(string name)
        {
            return new HttpClient();
        }
    }
}
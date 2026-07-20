using System.Net;
using Xunit;

namespace Server.Tests.Integration.Controllers;

public class HealthControllerTests : IClassFixture<CustomWebApplicationFactory>
{
    private readonly HttpClient _client;

    public HealthControllerTests(CustomWebApplicationFactory factory)
    {
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task GetHealth_WhenCalled_Returns200()
    {
        var response = await _client.GetAsync("/api/Health");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }
}

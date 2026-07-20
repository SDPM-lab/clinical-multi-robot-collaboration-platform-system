using Server.Services;
using Xunit;

namespace Server.Tests.Unit.Services;

public class TaskServiceTests
{
    private readonly TaskService _sut = new();

    public TaskServiceTests()
    {
        TaskService.ResetForTests();
    }

    [Fact]
    public async Task GetTasksAsync_WhenCalled_ReturnsSeededTasks()
    {
        var result = await _sut.GetTasksAsync();

        Assert.Equal(5, result.Count);
    }
}

namespace Server.Services;

public sealed class TaskScheduleWorker(IServiceScopeFactory scopeFactory) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(1));
        while (await timer.WaitForNextTickAsync(stoppingToken))
        {
            using var scope = scopeFactory.CreateScope();
            var service = (TaskService)scope.ServiceProvider.GetRequiredService<ITaskService>();
            await service.DispatchDueTasksAsync(stoppingToken);
        }
    }
}

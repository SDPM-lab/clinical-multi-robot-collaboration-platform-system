namespace Server.Services;

// 背景排程工作：由 ASP.NET Core 啟動與停止，每秒觸發一次到期任務檢查。
// scopeFactory 由依賴注入提供，用來取得每次檢查所需的服務。
public sealed class TaskScheduleWorker(IServiceScopeFactory scopeFactory, IWebHostEnvironment environment, IConfiguration configuration) : BackgroundService
{
    // 背景工作的執行入口；stoppingToken 會在應用程式停止時通知此工作取消。
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // 建立每秒觸發的計時器；離開方法時由 using 自動釋放資源。
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(1));

        // 非同步等待下一次觸發；收到停止通知後，等待會取消並結束背景工作。
        while (await timer.WaitForNextTickAsync(stoppingToken))
        {
            // 每輪建立獨立的服務作用範圍，並在本輪結束時釋放範圍內的服務。
            using var scope = scopeFactory.CreateScope();

            // 取得註冊的任務服務，轉為 TaskService 以呼叫內部的派送方法。
            var service = (TaskService)scope.ServiceProvider.GetRequiredService<ITaskService>();

            // 實際的時間與狀態檢查、派工提交由 TaskService 負責。
            if (environment.IsDevelopment() && configuration.GetValue<bool>("TaskDispatch:DevelopmentSimulation:Enabled")
                && !service.IsExternalDispatcherConfigured)
                await service.SimulateDueTasksAsync(scope.ServiceProvider.GetRequiredService<RobotStateStore>(), stoppingToken);
            else
                await service.DispatchDueTasksAsync(stoppingToken);
        }
    }
}

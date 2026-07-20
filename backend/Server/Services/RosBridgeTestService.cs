using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;

namespace Server.Services;

public class RosBridgeTestService : BackgroundService
{
    private readonly ILogger<RosBridgeTestService> _logger;
    private readonly RobotStateStore _store;
    private string _rosBridgeUrl;
    private bool _shouldConnect;
    private int _retryCount;
    private CancellationTokenSource? _reconnectCts;
    private readonly SemaphoreSlim _connectSignal = new(0);
    private readonly object _lock = new();
    private readonly ConcurrentDictionary<string, TaskProgressInfo> _taskProgress = new();
    private readonly ConcurrentDictionary<string, int> _lastBattery = new();

    private sealed class TaskProgressInfo
    {
        public string TaskId = "";
        public bool HasMoved;
        public double PrevX, PrevY;
        public double TotalDistanceTraveled;
        public double EstimatedTotalDistance;
        public DateTimeOffset StartedAt;
    }

    private static readonly Dictionary<int, string> ModeNames = new()
    {
        [0] = "待命",
        [1] = "充電中",
        [2] = "移動中",
        [3] = "暫停",
        [4] = "等待中",
        [5] = "緊急停止",
    };

    private readonly ConcurrentDictionary<string, string> _nearestWaypoints = new();
    private readonly ConcurrentDictionary<string, string> _robotUptimes = new();
    private DateTimeOffset _lastFleetUpdate = DateTimeOffset.MinValue;
    private static readonly TimeSpan FleetUpdateInterval = TimeSpan.FromSeconds(1);

    private int SmoothedBattery(string rosName, double raw)
    {
        var rounded = (int)Math.Round(raw);
        var prev = _lastBattery.GetOrAdd(rosName, rounded);
        if (Math.Abs(rounded - prev) >= 2)
        {
            _lastBattery[rosName] = rounded;
            return rounded;
        }
        return prev;
    }

    public RosBridgeTestService(ILogger<RosBridgeTestService> logger, IConfiguration config, RobotStateStore store)
    {
        _logger = logger;
        _store = store;
        _rosBridgeUrl = config.GetValue<string>("RosBridge:Url") ?? "ws://localhost:9090";
        _store.RosBridgeUrl = _rosBridgeUrl;
    }

    public void Connect(string url)
    {
        lock (_lock)
        {
            if (_shouldConnect && _rosBridgeUrl == url)
                return;

            var urlChanged = _rosBridgeUrl != url;
            _rosBridgeUrl = url;
            _store.RosBridgeUrl = url;
            _store.ConnectionStatus = "disconnected";
            _retryCount = 0;
            _store.RetryCount = 0;
            _shouldConnect = true;

            if (urlChanged)
            {
                _store.ClearRobots();
                _taskProgress.Clear();
                _nearestWaypoints.Clear();
                _robotUptimes.Clear();
                _lastBattery.Clear();
            }

            _reconnectCts?.Cancel();
            _connectSignal.Release();
        }
    }

    public void Disconnect()
    {
        lock (_lock)
        {
            _shouldConnect = false;
            _store.ClearRobots();
            _taskProgress.Clear();
            _nearestWaypoints.Clear();
            _reconnectCts?.Cancel();
        }
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("RosBridge 服務已啟動，等待使用者連線...");

        while (!stoppingToken.IsCancellationRequested)
        {
            if (!_shouldConnect)
            {
                try { await _connectSignal.WaitAsync(stoppingToken); }
                catch (OperationCanceledException) { break; }
            }

            _reconnectCts = CancellationTokenSource.CreateLinkedTokenSource(stoppingToken);
            var ct = _reconnectCts.Token;

            try
            {
                await ConnectAndListen(ct);
                _store.ConnectionStatus = "disconnected";
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                _retryCount++;
                _store.RetryCount = _retryCount;
                _logger.LogWarning("RosBridge 連線逾時（第 {Count} 次），5 秒後重試...", _retryCount);
                _store.ConnectionStatus = "disconnected";
            }
            catch (OperationCanceledException)
            {
                _store.ConnectionStatus = "disconnected";
                if (!_shouldConnect)
                {
                    _store.ClearRobots();
                    _logger.LogInformation("已中斷 RosBridge 連線");
                    continue;
                }
                _retryCount = 0;
                _logger.LogInformation("收到重連指令，正在以新 URL 連線...");
            }
            catch (Exception ex)
            {
                _retryCount++;
                _store.RetryCount = _retryCount;
                _logger.LogWarning(ex, "RosBridge 連線失敗（第 {Count} 次），5 秒後重試...", _retryCount);
                _store.ConnectionStatus = "disconnected";
            }

            if (_shouldConnect && !stoppingToken.IsCancellationRequested)
            {
                try { await Task.Delay(5000, stoppingToken); }
                catch (OperationCanceledException) { break; }
            }
        }
    }

    private async Task ConnectAndListen(CancellationToken ct)
    {
        using var ws = new ClientWebSocket();

        string url;
        lock (_lock) { url = _rosBridgeUrl; }

        _logger.LogInformation("正在連線到 RosBridge: {Url}", url);
        _store.ConnectionStatus = "connecting";

        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeoutCts.CancelAfter(TimeSpan.FromSeconds(5));
        await ws.ConnectAsync(new Uri(url), timeoutCts.Token);
        _logger.LogInformation("已連線到 RosBridge!");
        _retryCount = 0;
        _store.RetryCount = 0;
        _store.ConnectionStatus = "connected";

        var subscribe = JsonSerializer.Serialize(new
        {
            op = "subscribe",
            topic = "/fleet_states",
            type = "rmf_fleet_msgs/msg/FleetState",
        });
        await ws.SendAsync(Encoding.UTF8.GetBytes(subscribe), WebSocketMessageType.Text, true, ct);

        var subscribeWaypoint = JsonSerializer.Serialize(new
        {
            op = "subscribe",
            topic = "/robot_nearest_waypoint",
        });
        await ws.SendAsync(Encoding.UTF8.GetBytes(subscribeWaypoint), WebSocketMessageType.Text, true, ct);
        _logger.LogInformation("已訂閱 /fleet_states 及 /robot_nearest_waypoint，等待資料...");

        var buffer = new byte[1024 * 64];
        while (ws.State == WebSocketState.Open && !ct.IsCancellationRequested)
        {
            using var ms = new MemoryStream();
            WebSocketReceiveResult result;
            do
            {
                result = await ws.ReceiveAsync(buffer, ct);
                ms.Write(buffer, 0, result.Count);
            } while (!result.EndOfMessage);

            if (result.MessageType == WebSocketMessageType.Close)
                break;

            var json = Encoding.UTF8.GetString(ms.ToArray());
            ProcessMessage(json);
        }
    }

    private void ProcessMessage(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            if (!root.TryGetProperty("op", out var op) || op.GetString() != "publish")
                return;

            var topic = root.TryGetProperty("topic", out var t) ? t.GetString() : "";
            if (topic == "/robot_nearest_waypoint")
            {
                ProcessWaypointMessage(root.GetProperty("msg"));
                return;
            }

            var now = DateTimeOffset.Now;
            if (now - _lastFleetUpdate < FleetUpdateInterval)
                return;
            _lastFleetUpdate = now;

            var msg = root.GetProperty("msg");
            var fleetName = msg.GetProperty("name").GetString() ?? "";

            foreach (var robot in msg.GetProperty("robots").EnumerateArray())
            {
                var rosName = robot.GetProperty("name").GetString() ?? "";
                var model = robot.GetProperty("model").GetString() ?? "";
                var battery = robot.GetProperty("battery_percent").GetDouble();

                var smoothed = SmoothedBattery(rosName, battery);
                _logger.LogDebug("[{Name}] battery_percent 原始={Raw:F2} → 顯示={Smoothed}", rosName, battery, smoothed);
                var taskId = robot.GetProperty("task_id").GetString() ?? "";
                var mode = robot.GetProperty("mode").GetProperty("mode").GetInt32();

                var loc = robot.GetProperty("location");
                var x = loc.GetProperty("x").GetDouble();
                var y = loc.GetProperty("y").GetDouble();
                var yaw = loc.GetProperty("yaw").GetDouble();
                var level = loc.GetProperty("level_name").GetString() ?? "";

                int pathLen = 0;
                JsonElement pathArray = default;
                if (robot.TryGetProperty("path", out pathArray))
                    pathLen = pathArray.GetArrayLength();

                var mapping = _store.GetMapping(rosName);
                var id = mapping?.Id ?? rosName;
                var name = mapping?.Name ?? rosName;
                var modeText = ModeNames.GetValueOrDefault(mode, $"未知({mode})");

                var status = mode switch
                {
                    5 => "緊急停止",
                    _ when !string.IsNullOrEmpty(taskId) => "執行任務中",
                    0 => "待命",
                    1 => "充電中",
                    2 or 4 => "忙碌",
                    3 => "暫停",
                    _ => "在線",
                };

                if (!string.IsNullOrEmpty(taskId) && mode != 5)
                    modeText = "執行任務中";

                int progress = 0;
                string step;
                string startedAt = "—";
                string eta = "—";

                if (!string.IsNullOrEmpty(taskId))
                {
                    var tracker = _taskProgress.GetOrAdd(rosName, _ => new TaskProgressInfo());

                    if (tracker.TaskId != taskId)
                    {
                        tracker.TaskId = taskId;
                        tracker.HasMoved = false;
                        tracker.PrevX = x;
                        tracker.PrevY = y;
                        tracker.TotalDistanceTraveled = 0;
                        tracker.EstimatedTotalDistance = 0;
                        tracker.StartedAt = DateTimeOffset.Now;
                    }

                    if (mode == 2)
                        tracker.HasMoved = true;

                    var moved = Math.Sqrt(Math.Pow(x - tracker.PrevX, 2) + Math.Pow(y - tracker.PrevY, 2));
                    if (moved > 0.01)
                        tracker.TotalDistanceTraveled += moved;
                    tracker.PrevX = x;
                    tracker.PrevY = y;

                    if (pathLen > 0)
                    {
                        double remainDist = 0;
                        double px = x, py = y;
                        foreach (var wp in pathArray.EnumerateArray())
                        {
                            double wx = wp.GetProperty("x").GetDouble();
                            double wy = wp.GetProperty("y").GetDouble();
                            remainDist += Math.Sqrt(Math.Pow(wx - px, 2) + Math.Pow(wy - py, 2));
                            px = wx; py = wy;
                        }
                        var newEstimate = tracker.TotalDistanceTraveled + remainDist;
                        if (newEstimate > tracker.EstimatedTotalDistance)
                            tracker.EstimatedTotalDistance = newEstimate;
                    }

                    if (tracker.EstimatedTotalDistance > 0.1)
                    {
                        progress = (int)Math.Clamp(
                            tracker.TotalDistanceTraveled / tracker.EstimatedTotalDistance * 100, 0, 99);
                    }
                    else if (tracker.HasMoved)
                    {
                        var elapsed = (DateTimeOffset.Now - tracker.StartedAt).TotalSeconds;
                        progress = (int)Math.Min(elapsed / 60.0 * 90, 90);
                    }

                    if (mode == 0 && tracker.HasMoved)
                        progress = 100;

                    startedAt = tracker.StartedAt.ToString("HH:mm");

                    if (progress >= 100)
                    {
                        eta = "已完成";
                    }
                    else if (progress > 5)
                    {
                        var elapsed = DateTimeOffset.Now - tracker.StartedAt;
                        var estimatedTotal = elapsed.TotalSeconds / (progress / 100.0);
                        var remainingSec = estimatedTotal - elapsed.TotalSeconds;
                        if (remainingSec > 60)
                            eta = $"約 {(int)(remainingSec / 60)} 分鐘";
                        else if (remainingSec > 0)
                            eta = $"約 {(int)remainingSec} 秒";
                    }

                    step = mode switch
                    {
                        2 => "移動中",
                        4 => "等待中",
                        0 when progress >= 100 => "任務完成",
                        0 => "準備出發",
                        _ => ModeNames.GetValueOrDefault(mode, "執行中"),
                    };

                    _logger.LogDebug("任務進度 [{Name}] task={Task} mode={Mode} pathLen={Path} moved={Moved} dist={Dist:F2}/{Est:F2} progress={Prog}%",
                        rosName, taskId, mode, pathLen, tracker.HasMoved, tracker.TotalDistanceTraveled, tracker.EstimatedTotalDistance, progress);
                }
                else
                {
                    step = "待命中";
                    _taskProgress.TryRemove(rosName, out _);
                }

                var dto = new RobotDto
                {
                    Id = id,
                    RosName = rosName,
                    Name = name,
                    Model = model,
                    Status = status,
                    Battery = smoothed,
                    CurrentTask = string.IsNullOrEmpty(taskId) ? "無任務" : $"執行任務: {taskId}",
                    Location = _nearestWaypoints.TryGetValue(rosName, out var nearestWp) ? $"{level} — {nearestWp}" : level,
                    X = Math.Round(x, 2),
                    Y = Math.Round(y, 2),
                    Yaw = Math.Round(yaw, 4),
                    LevelName = level,
                    Signal = "良好",
                    Uptime = _robotUptimes.TryGetValue(rosName, out var uptimeVal) ? uptimeVal : "",
                    Mode = mode,
                    ModeText = modeText,
                    ConnectionIp = _rosBridgeUrl,
                    Firmware = fleetName,
                    LastUpdate = DateTimeOffset.Now,
                    CurrentTaskDetail = new RobotTaskDetailDto
                    {
                        TaskNo = string.IsNullOrEmpty(taskId) ? "—" : taskId,
                        Title = string.IsNullOrEmpty(taskId) ? "尚未派遣" : $"任務 {taskId}",
                        Progress = progress,
                        Step = step,
                        StartedAt = startedAt,
                        Eta = eta,
                        Payload = "無",
                    },
                };

                _store.Update(rosName, dto);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "處理 RosBridge 訊息時發生錯誤");
        }
    }

    private void ProcessWaypointMessage(JsonElement msg)
    {
        try
        {
            var dataStr = msg.GetProperty("data").GetString();
            if (string.IsNullOrEmpty(dataStr)) return;

            using var arr = JsonDocument.Parse(dataStr);
            foreach (var entry in arr.RootElement.EnumerateArray())
            {
                var robotName = entry.GetProperty("robot").GetString() ?? "";
                var waypoint = entry.GetProperty("nearest_waypoint").GetString() ?? "";
                if (!string.IsNullOrEmpty(robotName) && !string.IsNullOrEmpty(waypoint))
                {
                    _nearestWaypoints[robotName] = waypoint;
                }
                if (!string.IsNullOrEmpty(robotName) && entry.TryGetProperty("uptime", out var uptimeEl))
                {
                    _robotUptimes[robotName] = uptimeEl.GetString() ?? "";
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "處理 waypoint 訊息失敗: {Raw}", msg.ToString());
        }
    }

}

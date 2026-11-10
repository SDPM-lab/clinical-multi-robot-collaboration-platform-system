using System.Collections.Concurrent;
using Server.Models;

namespace Server.Services;

public class RobotStateStore
{
    private readonly ConcurrentDictionary<string, RobotDto> _robots = new();
    private readonly ConcurrentDictionary<string, string> _robotNameMapping = new();
    private readonly ConcurrentDictionary<string, bool> _knownRosNames = new();
    private readonly ConcurrentDictionary<string, RobotRegistration> _registrations = new();

    public string RosBridgeUrl { get; set; } = string.Empty;
    public string ConnectionStatus { get; set; } = "disconnected";
    public string FailMessage { get; set; } = string.Empty;
    public int RetryCount { get; set; }

    public RobotStateStore()
    {
        for (var index = 1; index <= 7; index++)
        {
            var rosName = $"hospital_robot_{index}";
            var id = index switch { 1 => "robot-a", 2 => "robot-b", _ => $"robot-{rosName}" };
            var name = index switch
            {
                1 => "C01",
                2 => "C02",
                3 => "M01",
                4 => "M02",
                5 => "W01",
                6 => "W02",
                _ => "W03",
            };
            var robotType = index <= 2 ? "clean" : index <= 4 ? "medical" : "ward";
            _registrations[rosName] = new(id, rosName, name, LevelName: "L1", RobotType: robotType);
            _robotNameMapping[rosName] = name;
            _knownRosNames[rosName] = true;
        }
    }

    public void Update(string rosName, RobotDto dto)
    {
        dto.HasTelemetry = true;
        if (_registrations.TryGetValue(rosName, out var profile)) dto.RobotType = profile.RobotType;
        if (string.IsNullOrWhiteSpace(dto.LevelName) && _registrations.TryGetValue(rosName, out var registration))
            dto.LevelName = registration.LevelName;
        _robots.AddOrUpdate(rosName, dto, (_, _) => dto);
    }

    public List<RobotDto> GetAll() => _knownRosNames.Keys.Select(rosName =>
    {
        var mapping = GetMapping(rosName)!.Value;
        if (_robots.TryGetValue(rosName, out var state)) return state;
        // 使用名冊預設樓層；名冊存在不代表已收到定位或電量。
        return new RobotDto { Id = mapping.Id, RosName = rosName, Name = mapping.Name,
            Status = "離線", Signal = "未提供", HasTelemetry = false,
            RobotType = _registrations.TryGetValue(rosName, out var kind) ? kind.RobotType : "",
            LevelName = _registrations.TryGetValue(rosName, out var registration) ? registration.LevelName : "" };
    }).OrderBy(robot => robot.Id, StringComparer.Ordinal).ToList();

    public List<RobotRegistration> GetRegistrations() => _registrations.Values.OrderBy(r => r.RosName, StringComparer.Ordinal).ToList();

    public (string Id, string Name)? GetMapping(string rosName)
    {
        if (!_knownRosNames.ContainsKey(rosName)) return null;
        var name = _robotNameMapping.GetValueOrDefault(rosName, rosName);
        var id = $"robot-{rosName}";
        if (rosName == "hospital_robot_1") id = "robot-a";
        if (rosName == "hospital_robot_2") id = "robot-b";
        return (id, name);
    }

    public List<(string Id, string Name)> GetAllMappings()
    {
        return [.. _knownRosNames.Keys
            .OrderBy(rosName => rosName, StringComparer.Ordinal)
            .Select(GetMapping)
            .Where(m => m.HasValue)
            .Select(m => m!.Value)];
    }

    public List<string> GetPendingRobots()
    {
        return [.. _robots.Keys.Where(k => !_knownRosNames.ContainsKey(k))];
    }

    public bool ConfirmRobot(string rosName, string displayName)
    {
        // F1 名冊目前固定七台，不能用確認端點意外新增第八台。
        if (!_registrations.TryGetValue(rosName, out var registration)) return false;
        _registrations[rosName] = new(GetMapping(rosName)?.Id ?? $"robot-{rosName}", rosName, displayName,
            registration.LevelName, registration.RobotType);
        _robotNameMapping[rosName] = displayName;
        _knownRosNames[rosName] = true;
        return true;
    }

    public void ClearRobots()
    {
        _robots.Clear();
        FailMessage = string.Empty;
    }
}

public class RobotDto
{
    public bool HasTelemetry { get; set; }
    public string Id { get; set; } = string.Empty;
    public string RosName { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Model { get; set; } = string.Empty;
    public string RobotType { get; set; } = string.Empty;
    public string Status { get; set; } = "待命";
    public int Battery { get; set; }
    public string CurrentTask { get; set; } = string.Empty;
    public string Location { get; set; } = string.Empty;
    public double X { get; set; }
    public double Y { get; set; }
    public double Yaw { get; set; }
    public string LevelName { get; set; } = string.Empty;
    public string Signal { get; set; } = "良好";
    public string Uptime { get; set; } = string.Empty;
    public int CompletedToday { get; set; }
    public string ConnectionIp { get; set; } = string.Empty;
    public string Firmware { get; set; } = string.Empty;
    public int Mode { get; set; }
    public string ModeText { get; set; } = string.Empty;
    public DateTimeOffset LastUpdate { get; set; }
    public RobotTaskDetailDto CurrentTaskDetail { get; set; } = new();
}

public class RobotTaskDetailDto
{
    public string TaskNo { get; set; } = "—";
    public string Title { get; set; } = "尚未派遣";
    public int Progress { get; set; }
    public string Step { get; set; } = string.Empty;
    public string StartedAt { get; set; } = "—";
    public string Eta { get; set; } = "—";
    public string Payload { get; set; } = "無";
}

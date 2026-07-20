using System.Collections.Concurrent;

namespace Server.Services;

public class RobotStateStore
{
    private readonly ConcurrentDictionary<string, RobotDto> _robots = new();
    private readonly ConcurrentDictionary<string, string> _robotNameMapping = new();
    private readonly ConcurrentDictionary<string, bool> _knownRosNames = new();

    public string RosBridgeUrl { get; set; } = string.Empty;
    public string ConnectionStatus { get; set; } = "disconnected";
    public string FailMessage { get; set; } = string.Empty;
    public int RetryCount { get; set; }

    public RobotStateStore()
    {
        _robotNameMapping["hospital_robot_1"] = "機器人 A";
        _robotNameMapping["hospital_robot_2"] = "機器人 B";
        _knownRosNames["hospital_robot_1"] = true;
        _knownRosNames["hospital_robot_2"] = true;
    }

    public void Update(string rosName, RobotDto dto)
    {
        _robots.AddOrUpdate(rosName, dto, (_, _) => dto);
    }

    public List<RobotDto> GetAll() => [.. _robots.Values.Where(r => _knownRosNames.ContainsKey(r.RosName))];

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
            .Select(GetMapping)
            .Where(m => m.HasValue)
            .Select(m => m!.Value)];
    }

    public List<string> GetPendingRobots()
    {
        return [.. _robots.Keys.Where(k => !_knownRosNames.ContainsKey(k))];
    }

    public void ConfirmRobot(string rosName, string displayName)
    {
        _robotNameMapping[rosName] = displayName;
        _knownRosNames[rosName] = true;
    }

    public void ClearRobots()
    {
        _robots.Clear();
        FailMessage = string.Empty;
    }
}

public class RobotDto
{
    public string Id { get; set; } = string.Empty;
    public string RosName { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Model { get; set; } = string.Empty;
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

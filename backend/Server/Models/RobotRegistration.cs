namespace Server.Models;

// 獨立名冊資料，之後可由資料庫提供；不將靜態註冊資料當成即時定位。
public sealed record RobotRegistration(string Id, string RosName, string Name, string LevelName = "", string RobotType = "");

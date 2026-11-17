using Server.Services;
using Xunit;

namespace Server.Tests.Unit.Services;

public class RobotRegistrationTests
{
    [Fact]
    public void SevenRegistrationsDefaultToFirstFloorWithoutInventingTelemetry()
    {
        var store = new RobotStateStore();
        Assert.Equal(7, store.GetRegistrations().Count);
        var robots = store.GetAll();
        Assert.Equal(7, robots.Count);
        Assert.Equal(7, robots.Select(robot => robot.Id).Distinct().Count());
        Assert.All(robots, robot => { Assert.False(robot.HasTelemetry); Assert.Equal("離線",robot.Status); Assert.Equal("L1",robot.LevelName); });
        Assert.Equal("robot-a", store.GetMapping("hospital_robot_1")!.Value.Id);
        Assert.Equal("robot-b", store.GetMapping("hospital_robot_2")!.Value.Id);
        Assert.Equal("robot-hospital_robot_7", store.GetMapping("hospital_robot_7")!.Value.Id);
        Assert.Equal(new[] { "clean", "clean", "medical", "medical", "ward", "ward", "ward" },
            store.GetRegistrations().Select(registration => registration.RobotType));
        Assert.Equal(new[] { "C01", "C02", "M01", "M02", "W01", "W02", "W03" },
            store.GetRegistrations().Select(registration => registration.Name));
        Assert.All(store.GetRegistrations(), registration =>
        {
            Assert.Equal("agibot_g1", registration.Model);
            Assert.Equal("Agibot", registration.Manufacturer);
            Assert.Equal("agibot_g1_description", registration.DescriptionPackage);
            Assert.Equal(2, registration.Capabilities?.Length);
        });
        Assert.Equal(new[] { "robot-a", "robot-b", "robot-hospital_robot_3", "robot-hospital_robot_4",
                "robot-hospital_robot_5", "robot-hospital_robot_6", "robot-hospital_robot_7" },
            store.GetAllMappings().Select(mapping => mapping.Id));
    }

    [Fact]
    public void TelemetryUpdatesOneRegisteredRobotWithoutLosingOthers()
    {
        var store = new RobotStateStore();
        var mapping = store.GetMapping("hospital_robot_3")!.Value;
        store.Update("hospital_robot_3",new RobotDto { Id=mapping.Id, RosName="hospital_robot_3",Name=mapping.Name,LevelName="L1",X=1,Y=2,Status="待命",Battery=80 });
        var robot=Assert.Single(store.GetAll(),r=>r.Id==mapping.Id);
        Assert.True(robot.HasTelemetry);
        Assert.Equal("L1",robot.LevelName);
        Assert.Equal(7,store.GetAll().Count);
        store.ConfirmRobot("hospital_robot_3","Renamed robot");
        Assert.Equal("L1",store.GetRegistrations().Single(r=>r.RosName=="hospital_robot_3").LevelName);
        store.Update("hospital_robot_3", new RobotDto { Id=mapping.Id,RosName="hospital_robot_3",LevelName="L2" });
        Assert.Equal("L2",store.GetAll().Single(r=>r.Id==mapping.Id).LevelName);
        store.ClearRobots();
        Assert.Equal(7,store.GetRegistrations().Count);
        Assert.All(store.GetAll(),r=> { Assert.False(r.HasTelemetry);Assert.Equal("L1",r.LevelName); });
    }

    [Fact]
    public void UnknownRobotCannotBecomeAnEighthRegistration()
    {
        var store = new RobotStateStore();
        Assert.False(store.ConfirmRobot("hospital_robot_8", "Eighth"));
        Assert.Equal(7, store.GetRegistrations().Count);
        Assert.Equal(7, store.GetAll().Count);
    }
}

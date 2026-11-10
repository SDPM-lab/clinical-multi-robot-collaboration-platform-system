using Server.Models;
using Server.Services.Tasks;
using Xunit;

namespace Server.Tests.Unit.Services;

public class TaskProfileLocationsTests
{
    [Theory]
    [InlineData(TaskType.WasteTransport, "waste_return_2")]
    [InlineData(TaskType.ClothesCollection, "clothes_return_2")]
    [InlineData(TaskType.MedicationDelivery, "ward_a_2")]
    [InlineData(TaskType.SpecimenDelivery, "lab")]
    [InlineData(TaskType.WardService, "ward_a_2")]
    public void RejectsChargingStationAsTaskSourceOrDestination(TaskType type, string destination)
    {
        Assert.False(TaskProfileLocations.IsAllowed(type, "charging_station_2", destination));
        Assert.False(TaskProfileLocations.IsAllowed(type, destination, "charging_station_2"));
    }
}

using Microsoft.AspNetCore.Mvc;
using Server.Controllers;
using System.Text.Json;
using Xunit;

namespace Server.Tests.Unit.Controllers;

public class PlaceControllerTests
{
    [Fact]
    public void ListReturnsThePpoWaypointIdsInFixedObservationOrder()
    {
        var result = Assert.IsType<OkObjectResult>(new PlaceController().List());
        var places = JsonSerializer.SerializeToElement(result.Value).EnumerateArray().ToArray();
        var expectedIds = new[]
        {
            "charging_station_2", "ward_a_2", "ward_b_2", "consult_1_2",
            "consult_2_2", "consult_3_2", "nurse_station", "blood_draw",
            "x-ray", "ultrasound_2", "ecg_2", "therapy_room",
            "waste_return_2", "clothes_return_2", "pharmacy", "lab",
        };

        Assert.Equal(expectedIds.Length, places.Length);
        for (var index = 0; index < expectedIds.Length; index++)
        {
            Assert.Equal(index, places[index].GetProperty("index").GetInt32());
            Assert.Equal(expectedIds[index], places[index].GetProperty("id").GetString());
        }
    }
}

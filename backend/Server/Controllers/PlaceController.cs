using Microsoft.AspNetCore.Mvc;

namespace Server.Controllers;

[ApiController]
[Route("api/v1/place")]
public class PlaceController : ControllerBase
{
    [HttpGet]
    public IActionResult List()
    {
        var places = new[]
        {
            new { id = "ward_a",         name = "病房 A", type = "ward" },
            new { id = "ward_b",         name = "病房 B", type = "ward" },
            new { id = "ward_c",         name = "病房 C", type = "ward" },
            new { id = "ward_d",         name = "病房 D", type = "ward" },
            new { id = "nurse_station",  name = "護理站", type = "station" },
            new { id = "pharmacy",       name = "藥局", type = "department" },
            new { id = "lab",            name = "檢驗室", type = "department" },
            new { id = "consult_1",      name = "診間 1", type = "clinic" },
            new { id = "consult_2",      name = "診間 2", type = "clinic" },
            new { id = "consult_3",      name = "診間 3", type = "clinic" },
            new { id = "blood_draw",     name = "抽血區", type = "department" },
            new { id = "procedure_room", name = "處置室", type = "department" },
            new { id = "storage",        name = "倉儲區", type = "storage" },
        };

        return Ok(places);
    }
}

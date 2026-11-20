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
            new { index = 0,  id = "charging_station_2", name = "充電站 B", type = "charging" },
            new { index = 1,  id = "ward_a_2",           name = "病房 A", type = "ward" },
            new { index = 2,  id = "ward_b_2",           name = "病房 B", type = "ward" },
            new { index = 3,  id = "consult_1_2",        name = "門診 1 室", type = "clinic" },
            new { index = 4,  id = "consult_2_2",        name = "門診 2 室", type = "clinic" },
            new { index = 5,  id = "consult_3_2",        name = "門診 3 室", type = "clinic" },
            new { index = 6,  id = "nurse_station",      name = "護理站", type = "station" },
            new { index = 7,  id = "blood_draw",         name = "抽血區", type = "department" },
            new { index = 8,  id = "x-ray",              name = "X 光室", type = "department" },
            new { index = 9,  id = "ultrasound_2",       name = "超音波室", type = "department" },
            new { index = 10, id = "ecg_2",              name = "心電圖室", type = "department" },
            new { index = 11, id = "therapy_room",       name = "治療室", type = "department" },
            new { index = 12, id = "waste_return_2",     name = "廢棄物回收區", type = "return_point" },
            new { index = 13, id = "clothes_return_2",   name = "衣物回收區", type = "return_point" },
            new { index = 14, id = "pharmacy",           name = "藥局", type = "department" },
            new { index = 15, id = "lab",                name = "檢驗室", type = "department" },
        };

        return Ok(places);
    }
}

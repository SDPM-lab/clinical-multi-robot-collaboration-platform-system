using Microsoft.AspNetCore.Mvc;

namespace Server.Controllers;

[ApiController]
[Route("api/v1/place")]
public class PlaceController : ControllerBase
{
    private static readonly IReadOnlyList<object> Places =
    [
        new { id = "ward-3f",    name = "3F 病房", type = "ward"      },
        new { id = "ward-2f",    name = "2F 病房", type = "ward"      },
        new { id = "emergency",  name = "急診",    type = "emergency" },
        new { id = "corridor-1f",name = "1F 走廊", type = "corridor"  },
    ];

    [HttpGet]
    public IActionResult List() => Ok(Places);
}

using Microsoft.AspNetCore.Mvc;
using Server.Services;

namespace Server.Controllers;

[ApiController]
[Route("api/v1/robot")]
public class RobotInfoController : ControllerBase
{
    private readonly RobotStateStore _store;

    public RobotInfoController(RobotStateStore store) => _store = store;

    [HttpGet]
    public IActionResult List()
    {
        var robots = _store.GetAllMappings()
            .Select(m => new { id = m.Id, name = m.Name });
        return Ok(robots);
    }

}

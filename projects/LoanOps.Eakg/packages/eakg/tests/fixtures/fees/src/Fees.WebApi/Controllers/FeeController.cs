using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
namespace Fees.WebApi.Controllers {
    [Route("api/Fee")]
    [Authorize(Policy = AuthorizeUser.ApiUser)]
    [ApiController]
    public class FeeController : ControllerBase {
        [HttpGet("GetFee")]
        public IActionResult GetFee(long loanId) => Ok();
    }
}

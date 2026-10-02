using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
namespace Escrow.Api.Controllers {
    [Route("api/[controller]")]
    public class EscrowController : ControllerBase {
        [Route("GetEscrowByLoanNumber")]
        [HttpGet]
        [Authorize(Policy = AuthorizeUser.ApiUser)]
        public IActionResult GetEscrowByLoanNumber(long loanNumber) => Ok();
    }
}

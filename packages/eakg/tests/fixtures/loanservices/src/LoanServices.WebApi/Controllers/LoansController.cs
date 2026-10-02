using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
namespace LoanServices.WebApi.Controllers {
    [Route("api/[controller]")]
    public partial class LoansController : ControllerBase {
        [HttpGet("{id}/Summary")]
        [Authorize(Policy = ApiConstants.POLICY_DYNAMIC_API)]
        public async Task<LoanSummary> GetLoanSummary(long id) => null;
    }
}

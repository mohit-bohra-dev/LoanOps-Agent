using Microsoft.AspNetCore.Mvc;
namespace LoanServices.WebApi.Controllers {
    [Route("api/[controller]")]
    public class PaymentSchedulesController : ControllerBase {
        [HttpGet("/api/Loans/{id}/PaymentSchedules")]
        public IActionResult GetPaymentSchedules(long id) => Ok();
    }
}

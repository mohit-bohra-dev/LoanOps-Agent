# Synthetic mini-repos mirroring pilot evidence (no real hostnames/secrets).

## fees
### src/Fees.WebApi/Fees.WebApi.csproj
```xml
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup>
  <ItemGroup>
    <PackageReference Include="PNMAC.AppServices.AppAuth.AspNetCore" Version="6.5.0" />
    <PackageReference Include="PNMAC.LoanServices.Client" Version="8.0.0-rc" />
    <PackageReference Include="PNMAC.LoanServices.Domain" Version="8.12.0-rc" />
  </ItemGroup>
</Project>
```

### src/Fees.WebApi/Controllers/FeeController.cs
```csharp
namespace Fees.WebApi.Controllers
{
    [Route("api/Fee")]
    [Authorize(Policy = AuthorizeUser.ApiUser)]
    [ApiController]
    public class FeeController : ControllerBase
    {
        [HttpGet("GetFee")]
        public IActionResult GetFee(long loanId) => Ok();
    }
}
```

### src/Fees.BusinessLayer/LoanServiceApi.cs
```csharp
namespace Fees.BusinessLayer
{
    public class LoanServiceApi : RestClient
    {
        public LoanServiceApi(IOptions<AppSettings> options, IRestHelper restHelper)
            : base(options.Value.LoanServicesUrl, restHelper, null)
        {
        }

        public async Task<LoanSummary> GetLoanSummary(long loanId)
        {
            string api = "api", controllerName = "Loans";
            string apiUrl = String.Format("/{0}/{1}/{2}/Summary?api-version=1.0", api, controllerName, loanId);
            return await Get<LoanSummary>(apiUrl);
        }

        public async Task<List<PaymentSchedule>> GetPaymentSchedules(long loanId)
        {
            string api = "api", controllerName = "Loans", methodName = "PaymentSchedules";
            string apiUrl = String.Format("/{0}/{1}/{2}/{3}", api, controllerName, loanId, methodName);
            return await Get<List<PaymentSchedule>>(apiUrl);
        }
    }
}
```

### src/Fees.WebApi/appsettings.json
```json
{
  "AppSettings": {
    "LoanServicesUrl": "https://loanservicesapi.example.invalid",
    "TransactionPostedTopicName": "arn:aws:sns:us-west-2:000000000000:svt-dev-FinancialTransactionPosted"
  },
  "ConnectionStrings": {
    "FeeDataContext": "Server=sql.example.invalid;Database=Fee;",
    "LoanServicesContext": "Server=sql.example.invalid;Database=LoanServicing;"
  }
}
```

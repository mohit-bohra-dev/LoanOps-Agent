namespace Fees.BusinessLayer {
    public class LoanServiceApi : RestClient {
        public LoanServiceApi(IOptions<AppSettings> options, IRestHelper restHelper)
            : base(options.Value.LoanServicesUrl, restHelper, null) { }
        public async Task<LoanSummary> GetLoanSummary(long loanId) {
            string api = "api", controllerName = "Loans";
            string apiUrl = String.Format("/{0}/{1}/{2}/Summary?api-version=1.0", api, controllerName, loanId);
            return await Get<LoanSummary>(apiUrl);
        }
        public async Task<List<PaymentSchedule>> GetPaymentSchedules(long loanId) {
            string api = "api", controllerName = "Loans", methodName = "PaymentSchedules";
            string apiUrl = String.Format("/{0}/{1}/{2}/{3}", api, controllerName, loanId, methodName);
            return await Get<List<PaymentSchedule>>(apiUrl);
        }
    }
}

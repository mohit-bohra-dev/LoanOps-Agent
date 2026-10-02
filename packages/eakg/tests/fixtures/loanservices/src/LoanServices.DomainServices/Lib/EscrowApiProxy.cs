namespace LoanServices.DomainServices.Lib {
    public interface IEscrowApiProxy { }
    internal sealed class EscrowApiProxy : Auth0ServiceProxy, IEscrowApiProxy {
        public EscrowApiProxy(IRestHelper restHelper, IOptionsMonitor<ServiceUrlsConfiguration> serviceUrlsMonitor)
            : base(new ServiceUrlMonitorResolver(serviceUrlsMonitor, c => c.EscrowManagerApiUrl), restHelper) { }
    }
}

param location str
param clusterName str
param identityId str

resource aks 'Microsoft.ContainerService/managedClusters@2023-05-02-preview' = {
  name: clusterName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    dnsPrefix: clusterName
    agentPoolProfiles: [
      {
        name: 'syspool'
        count: 1
        vmSize: 'Standard_D2s_v3'
        osType: 'Linux'
        mode: 'System'
      }
      {
        name: 'userpool'
        count: 1
        vmSize: 'Standard_D4s_v3'
        osType: 'Linux'
        mode: 'User'
      }
    ]
  }
}

output aksId str = aks.id

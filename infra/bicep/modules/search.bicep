param location str
param searchName str

resource search 'Microsoft.Search/searchServices@2022-09-01' = {
  name: searchName
  location: location
  sku: {
    name: 'standard'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    publicNetworkAccess: 'enabled'
  }
}

output searchEndpoint str = 'https://${searchName}.search.windows.net'

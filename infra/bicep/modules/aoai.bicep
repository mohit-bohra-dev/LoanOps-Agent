param location str
param accountName str

resource cognitiveServices 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: accountName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled' // In a real prod this would be Disabled with a Private Endpoint
  }
}

resource deployment1 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: cognitiveServices
  name: 'gpt-4o'
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-05-13'
    }
  }
}

output endpoint str = cognitiveServices.properties.endpoint

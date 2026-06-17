param location str
param keyVaultName str
param principalId str

resource kv 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: principalId
        permissions: {
          secrets: ['get', 'list']
        }
      }
    ]
  }
}

output keyVaultUri str = kv.properties.vaultUri

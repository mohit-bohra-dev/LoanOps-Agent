param location str
param identityName str

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

output id str = identity.id
output principalId str = identity.properties.principalId

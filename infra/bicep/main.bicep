targetScope = 'subscription'

param location str = 'eastus'
param envName str = 'dev'
param appName str = 'servicing-agent'

var rgName = 'rg-${appName}-${envName}-${location}'

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: rgName
  location: location
}

module identity 'modules/identity.bicep' = {
  scope: rg
  name: 'identityDeploy'
  params: {
    location: location
    identityName: 'mi-${appName}-${envName}'
  }
}

module monitoring 'modules/monitoring.bicep' = {
  scope: rg
  name: 'monitoringDeploy'
  params: {
    location: location
    logAnalyticsName: 'log-${appName}-${envName}'
    appInsightsName: 'appi-${appName}-${envName}'
  }
}

module keyvault 'modules/keyvault.bicep' = {
  scope: rg
  name: 'keyvaultDeploy'
  params: {
    location: location
    keyVaultName: 'kv-${appName}-${envName}'
    principalId: identity.outputs.principalId
  }
}

module aoai 'modules/aoai.bicep' = {
  scope: rg
  name: 'aoaiDeploy'
  params: {
    location: location
    accountName: 'oai-${appName}-${envName}'
  }
}

module search 'modules/search.bicep' = {
  scope: rg
  name: 'searchDeploy'
  params: {
    location: location
    searchName: 'srch-${appName}-${envName}'
  }
}

module aks 'modules/aks.bicep' = {
  scope: rg
  name: 'aksDeploy'
  params: {
    location: location
    clusterName: 'aks-${appName}-${envName}'
    identityId: identity.outputs.id
  }
}

module appservice 'modules/appservice.bicep' = {
  scope: rg
  name: 'appserviceDeploy'
  params: {
    location: location
    planName: 'plan-${appName}-${envName}'
    appName: 'app-${appName}-${envName}'
  }
}

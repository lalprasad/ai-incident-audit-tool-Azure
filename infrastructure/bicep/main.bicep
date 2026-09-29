@description('Skeleton composition for a later deployment. Do not deploy this from the MVP.')
param location string = resourceGroup().location
param tenantId string
param storageAccountName string
param openAiAccountName string
param documentAccountName string
param searchName string
param cosmosAccountName string
param vaultName string
param appName string

module storage 'storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    storageAccountName: storageAccountName
  }
}

module openai 'openai.bicep' = {
  name: 'openai'
  params: {
    location: location
    accountName: openAiAccountName
  }
}

module documentIntelligence 'document-intelligence.bicep' = {
  name: 'document-intelligence'
  params: {
    location: location
    accountName: documentAccountName
  }
}

module search 'search.bicep' = {
  name: 'search'
  params: {
    location: location
    searchName: searchName
  }
}

module cosmos 'cosmos.bicep' = {
  name: 'cosmos'
  params: {
    location: location
    accountName: cosmosAccountName
  }
}

module keyVault 'keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    vaultName: vaultName
    tenantId: tenantId
  }
}

module app 'appservice.bicep' = {
  name: 'appservice'
  params: {
    location: location
    appName: appName
    vaultName: keyVault.outputs.vaultName
  }
}

output storageId string = storage.outputs.id
output openAiEndpoint string = openai.outputs.endpoint
output documentEndpoint string = documentIntelligence.outputs.endpoint
output searchEndpoint string = search.outputs.endpoint
output cosmosEndpoint string = cosmos.outputs.endpoint
output appId string = app.outputs.id

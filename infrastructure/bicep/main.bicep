@description('Deploy Incident Audit Azure AI stack: OpenAI, Document Intelligence, Storage, Cosmos, Key Vault, App Service.')
targetScope = 'resourceGroup'

param location string = resourceGroup().location
param namePrefix string
param openAiDeploymentName string = 'gpt-4o-mini'
param openAiModelName string = 'gpt-4o-mini'
param openAiModelVersion string = '2024-07-18'
param dockerImage string
param acrLoginServer string = ''
param acrUsername string = ''
@secure()
param acrPassword string = ''
param deploySearch bool = false

var suffix = uniqueString(resourceGroup().id, namePrefix)
var storageAccountName = take(replace('${namePrefix}st${suffix}', '-', ''), 24)
var openAiAccountName = take('${namePrefix}-oai-${suffix}', 64)
var documentAccountName = take('${namePrefix}-di-${suffix}', 64)
var cosmosAccountName = take('${namePrefix}-cosmos-${suffix}', 44)
var vaultName = take('${namePrefix}-kv-${suffix}', 24)
var appName = take('${namePrefix}-app-${suffix}', 60)
var searchName = take('${namePrefix}-srch-${suffix}', 60)

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
    deploymentName: openAiDeploymentName
    modelName: openAiModelName
    modelVersion: openAiModelVersion
  }
}

module documentIntelligence 'document-intelligence.bicep' = {
  name: 'document-intelligence'
  params: {
    location: location
    accountName: documentAccountName
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
    tenantId: subscription().tenantId
  }
}

module search 'search.bicep' = if (deploySearch) {
  name: 'search'
  params: {
    location: location
    searchName: searchName
  }
}

module app 'appservice.bicep' = {
  name: 'appservice'
  params: {
    location: location
    appName: appName
    vaultName: keyVault.outputs.vaultName
    openAiEndpoint: openai.outputs.endpoint
    openAiDeployment: openai.outputs.deploymentName
    documentEndpoint: documentIntelligence.outputs.endpoint
    storageAccountUrl: 'https://${storage.outputs.name}.blob.core.windows.net'
    storageContainer: 'incident-audits'
    cosmosEndpoint: cosmos.outputs.endpoint
    cosmosDatabase: 'incident-audit'
    cosmosContainer: 'audits'
    frontendOrigins: 'https://${appName}.azurewebsites.net'
    dockerImage: dockerImage
    acrLoginServer: acrLoginServer
    acrUsername: acrUsername
    acrPassword: acrPassword
  }
}

// Allow the web app to read Key Vault secrets (RBAC)
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVault.outputs.vaultName
}

var secretsUserRole = '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User

resource appKvRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, app.outputs.principalId, secretsUserRole)
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRole)
    principalId: app.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

output appUrl string = 'https://${app.outputs.defaultHostName}'
output appName string = app.outputs.name
output openAiEndpoint string = openai.outputs.endpoint
output openAiDeployment string = openai.outputs.deploymentName
output openAiAccountName string = openAiAccountName
output documentEndpoint string = documentIntelligence.outputs.endpoint
output documentAccountName string = documentAccountName
output storageAccountName string = storage.outputs.name
output cosmosEndpoint string = cosmos.outputs.endpoint
output cosmosAccountName string = cosmosAccountName
output vaultName string = keyVault.outputs.vaultName
output appPrincipalId string = app.outputs.principalId

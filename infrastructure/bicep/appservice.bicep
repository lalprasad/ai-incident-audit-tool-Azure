@description('Linux App Service running the Incident Audit container (API + SPA).')
param location string
param appName string
param vaultName string
param openAiEndpoint string
param openAiDeployment string
param documentEndpoint string
param storageAccountUrl string
param storageContainer string
param cosmosEndpoint string
param cosmosDatabase string
param cosmosContainer string
param frontendOrigins string
param dockerImage string
param acrLoginServer string = ''
param acrUsername string = ''
@secure()
param acrPassword string = ''

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${appName}-plan'
  location: location
  sku: {
    name: 'B1'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource site 'Microsoft.Web/sites@2023-12-01' = {
  name: appName
  location: location
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${dockerImage}'
      alwaysOn: true
      acrUseManagedIdentityCreds: false
      appSettings: [
        { name: 'WEBSITES_PORT', value: '8000' }
        { name: 'DOCKER_REGISTRY_SERVER_URL', value: acrLoginServer }
        { name: 'DOCKER_REGISTRY_SERVER_USERNAME', value: acrUsername }
        { name: 'DOCKER_REGISTRY_SERVER_PASSWORD', value: acrPassword }
        { name: 'USE_MOCK_AZURE', value: 'false' }
        { name: 'SERVE_FRONTEND', value: 'true' }
        { name: 'AZURE_USE_MANAGED_IDENTITY', value: 'false' }
        { name: 'FRONTEND_ORIGINS', value: frontendOrigins }
        { name: 'AZURE_OPENAI_ENDPOINT', value: openAiEndpoint }
        { name: 'AZURE_OPENAI_DEPLOYMENT', value: openAiDeployment }
        { name: 'AZURE_OPENAI_API_VERSION', value: '2024-10-21' }
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: '@Microsoft.KeyVault(VaultName=${vaultName};SecretName=openai-api-key)'
        }
        { name: 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', value: documentEndpoint }
        {
          name: 'AZURE_DOCUMENT_INTELLIGENCE_KEY'
          value: '@Microsoft.KeyVault(VaultName=${vaultName};SecretName=document-intelligence-key)'
        }
        { name: 'AZURE_STORAGE_ACCOUNT_URL', value: storageAccountUrl }
        { name: 'AZURE_STORAGE_CONTAINER', value: storageContainer }
        {
          name: 'AZURE_STORAGE_CONNECTION_STRING'
          value: '@Microsoft.KeyVault(VaultName=${vaultName};SecretName=storage-connection-string)'
        }
        { name: 'AZURE_COSMOS_ENDPOINT', value: cosmosEndpoint }
        { name: 'AZURE_COSMOS_DATABASE', value: cosmosDatabase }
        { name: 'AZURE_COSMOS_CONTAINER', value: cosmosContainer }
        {
          name: 'AZURE_COSMOS_KEY'
          value: '@Microsoft.KeyVault(VaultName=${vaultName};SecretName=cosmos-key)'
        }
      ]
    }
  }
}

output id string = site.id
output name string = site.name
output defaultHostName string = site.properties.defaultHostName
output principalId string = site.identity.principalId

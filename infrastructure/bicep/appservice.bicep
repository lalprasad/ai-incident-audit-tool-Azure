@description('Skeleton only. App settings reference Key Vault and do not inline secrets.')
param location string
param appName string
param vaultName string
param linuxFxVersion string = 'PYTHON|3.12'

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
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: linuxFxVersion
      appSettings: [
        {
          name: 'USE_MOCK_AZURE'
          value: 'false'
        }
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: '@Microsoft.KeyVault(VaultName=${vaultName};SecretName=openai-api-key)'
        }
        {
          name: 'AZURE_DOCUMENT_INTELLIGENCE_KEY'
          value: '@Microsoft.KeyVault(VaultName=${vaultName};SecretName=document-intelligence-key)'
        }
        {
          name: 'AZURE_STORAGE_CONNECTION_STRING'
          value: '@Microsoft.KeyVault(VaultName=${vaultName};SecretName=storage-connection-string)'
        }
        {
          name: 'AZURE_COSMOS_KEY'
          value: '@Microsoft.KeyVault(VaultName=${vaultName};SecretName=cosmos-key)'
        }
      ]
    }
  }
}

output id string = site.id
output principalId string = site.identity.principalId

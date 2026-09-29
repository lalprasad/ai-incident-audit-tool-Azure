@description('Skeleton only. Secret values are not defined in this file.')
param location string
param vaultName string
param tenantId string
param openAiSecretName string = 'openai-api-key'
param documentSecretName string = 'document-intelligence-key'
param storageSecretName string = 'storage-connection-string'
param cosmosSecretName string = 'cosmos-key'

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

output vaultName string = vault.name
output vaultUri string = vault.properties.vaultUri
output secretNames array = [
  openAiSecretName
  documentSecretName
  storageSecretName
  cosmosSecretName
]

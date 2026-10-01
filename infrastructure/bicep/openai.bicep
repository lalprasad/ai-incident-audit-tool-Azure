@description('Azure OpenAI account with a chat deployment for the audit model.')
param location string
param accountName string
param deploymentName string = 'gpt-4o-mini'
param modelName string = 'gpt-4o-mini'
param modelVersion string = '2024-07-18'
param capacity int = 30

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: accountName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: deploymentName
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
  }
  sku: {
    name: 'Standard'
    capacity: capacity
  }
}

output endpoint string = openai.properties.endpoint
output id string = openai.id
output deploymentName string = deployment.name

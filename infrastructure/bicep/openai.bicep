@description('Skeleton only. Create the model deployment separately so this file does not choose a billable SKU.')
param location string
param accountName string

resource openai 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: accountName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
  }
}

output endpoint string = openai.properties.endpoint
output id string = openai.id

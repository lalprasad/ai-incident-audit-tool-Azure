@description('Skeleton only. Not deployed by the MVP.')
param location string
param accountName string

resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: accountName
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
  }
}

output endpoint string = documentIntelligence.properties.endpoint
output id string = documentIntelligence.id

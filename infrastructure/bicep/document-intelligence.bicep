@description('Azure AI Document Intelligence for PDF layout extraction.')
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

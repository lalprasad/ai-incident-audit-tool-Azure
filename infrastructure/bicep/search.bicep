@description('Skeleton only. The MVP loads the rubric from audit_criteria.json unless search is configured.')
param location string
param searchName string
param sku string = 'basic'

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchName
  location: location
  sku: {
    name: sku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
  }
}

output id string = search.id
output endpoint string = 'https://${search.name}.search.windows.net'

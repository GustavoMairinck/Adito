export type DataValue = string | number | boolean | null

export interface DataColumn {
  name: string
  type: string
}

export interface DataRelation {
  name: string
  label: string
  description: string
  kind: 'fact' | 'dimension' | 'entity'
  columns: DataColumn[]
  available: boolean
}

export interface ExplorerResult {
  rows: Record<string, DataValue>[]
  total: number
  page: number
  page_size: number
  distribution: Array<{ value: DataValue; count: number }>
}

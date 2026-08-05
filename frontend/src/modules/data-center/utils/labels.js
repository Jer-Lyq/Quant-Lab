export const freqOptions = [
  { label: '日线', value: 'daily' },
  { label: '周线', value: 'weekly' }
]

export const subChartOptions = [
  { label: '成交量', value: 'volume' },
  { label: 'RSI', value: 'rsi' },
  { label: 'MACD', value: 'macd' }
]

export function typeLabel(type) {
  return { stock: '股票', etf: 'ETF', index: '指数', fund: '基金' }[type] || type
}

export function createDefaultAnalytics() {
  return { overview: {}, factors: [], indicators: {} }
}

export function createDefaultDataSource() {
  return {
    provider: 'tushare',
    connection: { configured: false, token_masked: '', http_url: '', source: null, updated_at: null }
  }
}

export function createDefaultDataSourceForm() {
  return { tushare_token: '', tushare_http_url: 'https://tuaremax.top' }
}

export function createDefaultInstrumentForm() {
  return { ts_code: '', asset_type: 'stock', data_start: '2018-01-01', data_end: '' }
}

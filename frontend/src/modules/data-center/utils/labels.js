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
  return { stock: '股票', etf: 'ETF', index: '指数', fund: '基金', unknown: '待识别' }[type] || type
}

export function inferAssetType(tsCode) {
  const text = String(tsCode || '').trim().toUpperCase()
  const [code, exchange = ''] = text.split('.')
  if (!/^\d{6}$/.test(code)) return 'unknown'
  if (exchange === 'BJ') return 'stock'
  if (exchange === 'SH') {
    if (/^(600|601|603|605|688|689)/.test(code)) return 'stock'
    if (/^(510|511|512|513|515|516|517|518|520|560|561|562|563|588|589)/.test(code)) return 'etf'
    if (/^(000|880|881|882|883|884|885|886|887|888)/.test(code)) return 'index'
  }
  if (exchange === 'SZ') {
    if (/^(000|001|002|003|300|301)/.test(code)) return 'stock'
    if (/^(150|159|160|161|162|163|164|165|166|167|168|169|184)/.test(code)) return 'etf'
    if (/^(399|980|981|982|983|984|985|986|987|988)/.test(code)) return 'index'
  }
  return 'stock'
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
  return { ts_code: '', data_start: '2018-01-01', data_end: '' }
}

export function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: digits })
}

export function compactAxisNumber(value) {
  const number = Number(value)
  if (Number.isNaN(number)) return '-'
  const abs = Math.abs(number)
  if (abs >= 100000000) return `${trimNumber(number / 100000000)}亿`
  if (abs >= 10000) return `${trimNumber(number / 10000)}万`
  return trimNumber(number)
}

export function trimNumber(value) {
  return Number(value.toFixed(2)).toLocaleString('zh-CN')
}

export function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  return `${Number(value).toFixed(2)}%`
}

export function formatUnit(value, unit) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  return `${Number(value).toFixed(2)}${unit}`
}

export function factorValue(factor) {
  if (factor.value === null || factor.value === undefined || Number.isNaN(Number(factor.value))) return '-'
  if (factor.unit === '%') return formatPct(factor.value)
  if (factor.unit === 'x') return formatUnit(factor.value, 'x')
  return formatNumber(factor.value)
}

export function percentileWidth(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '0%'
  return `${Math.max(0, Math.min(100, Number(value)))}%`
}

export function percentileText(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '无分位'
  return `P${Number(value).toFixed(1)}`
}

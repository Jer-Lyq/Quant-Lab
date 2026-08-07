export const backtestStatusLabels = {
  pending: '准备中',
  queued: '排队中',
  running: '运行中',
  success: '已完成',
  failed: '失败',
  cancelled: '已取消'
}

export const activeBacktestStatuses = new Set(['pending', 'queued', 'running'])

export function formatPercent(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  })
}

export function formatDateTime(value) {
  if (!value) return '--'
  return String(value).replace('T', ' ').slice(0, 19)
}

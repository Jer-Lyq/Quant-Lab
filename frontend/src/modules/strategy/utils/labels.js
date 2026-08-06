export const strategyTypeOptions = [
  { label: '趋势', value: 'trend' },
  { label: '均值回归', value: 'mean_reversion' },
  { label: '突破', value: 'breakout' },
  { label: '动量', value: 'momentum' },
  { label: '择时', value: 'timing' },
  { label: '自定义', value: 'custom' }
]

export const strategyStatusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '待回测', value: 'ready' },
  { label: '回测中', value: 'backtesting' },
  { label: '已验证', value: 'validated' },
  { label: '废弃', value: 'discarded' }
]

export const userManagedStrategyStatusOptions = strategyStatusOptions.filter((item) =>
  ['draft', 'ready', 'discarded'].includes(item.value)
)

export const strategyFreqOptions = [
  { label: '日线', value: 'daily' },
  { label: '周线', value: 'weekly' }
]

export function strategyTypeLabel(value) {
  return strategyTypeOptions.find((item) => item.value === value)?.label || value
}

export function strategyStatusLabel(value) {
  return strategyStatusOptions.find((item) => item.value === value)?.label || value
}

export function strategyFreqLabel(value) {
  return strategyFreqOptions.find((item) => item.value === value)?.label || value
}

export function createDefaultStrategyForm() {
  return {
    name: '',
    description: '',
    strategy_idea: '',
    uploader_notes: '',
    strategy_type: 'custom',
    market: 'A股',
    freq: 'daily',
    status: 'draft'
  }
}

export function createDefaultVersionForm() {
  return {
    version_name: '',
    notes: '',
    code: `def init(context):
    # 初始化策略参数和全局状态
    pass


def handle_bar(context, bar_dict):
    # 每个 bar 调用一次，在这里写交易逻辑
    pass
`
  }
}

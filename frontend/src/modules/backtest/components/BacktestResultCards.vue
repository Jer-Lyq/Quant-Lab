<template>
  <div class="backtest-metric-grid">
    <div v-for="item in metrics" :key="item.label" class="backtest-metric">
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatNumber, formatPercent } from '../utils/labels'

const props = defineProps({ summary: { type: Object, default: () => ({}) } })

const metrics = computed(() => [
  { label: '总收益', value: formatPercent(props.summary.total_return) },
  { label: '年化收益', value: formatPercent(props.summary.annual_return) },
  { label: '最大回撤', value: formatPercent(props.summary.max_drawdown) },
  { label: '夏普比率', value: formatNumber(props.summary.sharpe) },
  { label: '年化波动', value: formatPercent(props.summary.volatility) },
  { label: '胜率', value: formatPercent(props.summary.win_rate) },
  { label: '成交次数', value: formatNumber(props.summary.trade_count, 0) }
])
</script>

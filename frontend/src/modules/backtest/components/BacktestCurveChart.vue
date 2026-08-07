<template>
  <section class="backtest-chart-panel">
    <div class="backtest-section-head compact">
      <div>
        <h3>收益路径</h3>
        <p class="subtle">净值与回撤按交易日对齐。</p>
      </div>
      <el-segmented v-model="mode" :options="chartModes" />
    </div>
    <div ref="chartRef" class="backtest-chart"></div>
  </section>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  equity: { type: Array, default: () => [] },
  drawdown: { type: Array, default: () => [] }
})

const chartRef = ref(null)
const mode = ref('equity')
const chartModes = [{ label: '净值', value: 'equity' }, { label: '回撤', value: 'drawdown' }]
let chart

async function render() {
  await nextTick()
  if (!chartRef.value) return
  chart = chart || echarts.init(chartRef.value)
  const isEquity = mode.value === 'equity'
  const rows = isEquity ? props.equity : props.drawdown
  const values = rows.map((item) => isEquity ? item.unit_net_value : item.drawdown)
  chart.setOption({
    animationDuration: 260,
    animationEasing: 'cubicOut',
    grid: { left: 58, right: 24, top: 22, bottom: 44 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#13231b',
      borderWidth: 0,
      textStyle: { color: '#f8faf7' },
      valueFormatter: (value) => isEquity ? Number(value).toFixed(4) : `${(Number(value) * 100).toFixed(2)}%`
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: rows.map((item) => String(item.date).slice(0, 10)),
      axisLine: { lineStyle: { color: '#cbd6cd' } },
      axisLabel: { color: '#66746b', hideOverlap: true }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLabel: {
        color: '#66746b',
        formatter: (value) => isEquity ? Number(value).toFixed(2) : `${(Number(value) * 100).toFixed(0)}%`
      },
      splitLine: { lineStyle: { color: '#e7eee8' } }
    },
    series: [{
      type: 'line',
      name: isEquity ? '单位净值' : '回撤',
      data: values,
      symbol: 'none',
      smooth: false,
      lineStyle: { width: 2, color: isEquity ? '#2f7d5b' : '#b65245' },
      areaStyle: { color: isEquity ? 'rgba(47, 125, 91, 0.09)' : 'rgba(182, 82, 69, 0.09)' }
    }]
  }, true)
}

const resize = () => chart?.resize()
watch(() => [props.equity, props.drawdown, mode.value], render, { deep: true })
onMounted(() => {
  window.addEventListener('resize', resize)
  render()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
})
</script>

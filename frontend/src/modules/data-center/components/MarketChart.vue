<template>
  <section class="chart-panel">
    <div class="panel-title-row">
      <div>
        <h3>价格与指标</h3>
        <p class="subtle">K线、均线、布林带、成交量与副图指标。</p>
      </div>
      <div class="layer-controls">
        <el-checkbox-group v-model="layersModel">
          <el-checkbox-button label="ma5">MA5</el-checkbox-button>
          <el-checkbox-button label="ma10">MA10</el-checkbox-button>
          <el-checkbox-button label="ma20">MA20</el-checkbox-button>
          <el-checkbox-button label="ma60">MA60</el-checkbox-button>
          <el-checkbox-button label="boll">BOLL</el-checkbox-button>
        </el-checkbox-group>
        <el-segmented v-model="subChartModel" :options="subChartOptions" />
      </div>
    </div>
    <div ref="chartRef" class="chart"></div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { buildMarketChartOptions } from '../utils/chartOptions'
import { subChartOptions } from '../utils/labels'

const props = defineProps({
  bars: {
    type: Array,
    default: () => []
  },
  indicators: {
    type: Object,
    default: () => ({})
  },
  priceLayers: {
    type: Array,
    default: () => []
  },
  subChart: {
    type: String,
    default: 'volume'
  }
})

const emit = defineEmits(['update:priceLayers', 'update:subChart'])
const chartRef = ref(null)
let chart

const layersModel = computed({
  get: () => props.priceLayers,
  set: (value) => emit('update:priceLayers', value)
})
const subChartModel = computed({
  get: () => props.subChart,
  set: (value) => emit('update:subChart', value)
})

async function renderChart() {
  await nextTick()
  if (!chartRef.value) return
  chart = chart || echarts.init(chartRef.value)
  chart.setOption(
    buildMarketChartOptions({
      bars: props.bars,
      indicators: props.indicators,
      priceLayers: props.priceLayers,
      subChart: props.subChart,
      chartHeight: chartRef.value.clientHeight || 680
    }),
    true
  )
}

const resizeChart = () => chart?.resize()

watch(
  () => [props.bars, props.indicators, props.priceLayers, props.subChart],
  renderChart,
  { deep: true }
)

onMounted(() => {
  window.addEventListener('resize', resizeChart)
  renderChart()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
})
</script>

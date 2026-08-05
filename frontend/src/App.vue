<template>
  <main class="app-shell">
    <!-- THESIS: Quant Lab is a data research desk, not a learning diary; the surface organizes market evidence for inspection.
    OWN-WORLD: Dark instrument rail, pale research canvas, white analysis sheets, green action state, compact tabular numerals.
    STORY: Login, choose or sync a symbol, then read price, volume, indicator, factor, and raw bar evidence in one flow.
    FIRST VIEWPORT: Session bar on top, instrument rail left, command strip and analytics grid right, with the chart as the primary artifact.
    FORM: Established operate workbench; no new visual-world seed needed.
    FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md -->
    <section v-if="!token" class="login-screen">
      <div class="login-panel">
        <div>
          <p class="product-mark">Quant Lab</p>
          <h1>量化研究数据工作台</h1>
          <p class="subtle">登录后查看已录入标的，管理员可以通过 Tushare 同步行情数据。</p>
        </div>
        <el-form label-position="top" @submit.prevent="login">
          <el-form-item label="账号">
            <el-input v-model="loginForm.username" autocomplete="username" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="loginForm.password" type="password" autocomplete="current-password" show-password />
          </el-form-item>
          <el-button type="primary" class="wide-button" :loading="loading" @click="login">
            <LogIn :size="18" />
            登录
          </el-button>
        </el-form>
      </div>
    </section>

    <section v-else class="workspace">
      <header class="topbar">
        <div>
          <p class="product-mark">Quant Lab</p>
          <h1>数据中心</h1>
        </div>
        <div class="topbar-actions">
          <span class="user-pill">{{ user?.username }} · {{ roleLabel }}</span>
          <el-button @click="logout">退出</el-button>
        </div>
      </header>

      <div class="layout">
        <aside class="sidebar">
          <div class="sidebar-head">
            <h2>研究标的</h2>
            <el-button class="sidebar-refresh" circle :disabled="loading" @click="loadInstruments">
              <RefreshCw :size="15" :class="{ 'is-refreshing': loading }" />
            </el-button>
          </div>
          <el-input v-model="keyword" placeholder="搜索代码或名称">
            <template #prefix><Search :size="16" /></template>
          </el-input>
          <div class="instrument-list">
            <button
              v-for="item in filteredInstruments"
              :key="item.id"
              class="instrument-item"
              :class="{ active: selected?.id === item.id }"
              @click="selectInstrument(item)"
            >
              <span>
                <strong>{{ item.name }}</strong>
                <small>{{ item.ts_code }} · {{ typeLabel(item.asset_type) }}</small>
              </span>
              <em>{{ item.status }}</em>
            </button>
          </div>
        </aside>

        <section class="content">
          <div v-if="isAdmin" class="admin-tools">
            <section class="admin-panel">
              <div class="panel-title-row">
                <div>
                  <h2>管理员录入</h2>
                  <p class="subtle">录入标的后同步行情，前台只展示已发布的数据。</p>
                </div>
              </div>
              <div class="admin-grid">
                <el-input v-model="newInstrument.ts_code" placeholder="例如 000001.SZ" />
                <el-select v-model="newInstrument.asset_type">
                  <el-option label="股票" value="stock" />
                  <el-option label="ETF" value="etf" />
                  <el-option label="基金" value="fund" />
                </el-select>
                <el-date-picker v-model="newInstrument.data_start" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" />
                <el-date-picker v-model="newInstrument.data_end" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" />
                <el-button class="admin-action-button" type="primary" :loading="loading" @click="createAndSync">
                  <Plus :size="16" />
                  新增并同步
                </el-button>
              </div>
            </section>

            <section class="admin-panel data-source-panel">
              <div class="panel-title-row">
                <div>
                  <h2>数据源接口</h2>
                  <p class="subtle">Token 和接口地址都可随时改，保存后同步会立刻走新配置。</p>
                  <p class="subtle">当前接口：{{ dataSource.connection.http_url || dataSourceForm.tushare_http_url }}</p>
                </div>
                <span class="source-status" :class="{ ready: dataSource.connection.configured }">
                  {{ dataSource.connection.configured ? '已配置' : '未配置' }}
                  <template v-if="dataSource.connection.token_masked"> · {{ dataSource.connection.token_masked }}</template>
                </span>
              </div>
              <div class="data-source-grid">
                <input
                  v-model="dataSourceForm.tushare_token"
                  class="source-input"
                  type="text"
                  placeholder="粘贴新的 Tushare Token"
                  autocomplete="off"
                  spellcheck="false"
                />
                <input
                  v-model="dataSourceForm.tushare_http_url"
                  class="source-input"
                  type="url"
                  placeholder="https://tuaremax.top"
                  autocomplete="off"
                  spellcheck="false"
                />
                <el-button :loading="loading" @click="saveDataSource">
                  <KeyRound :size="16" />
                  保存接口
                </el-button>
                <el-button type="primary" :disabled="!selected" :loading="loading" @click="saveAndSyncSelected">
                  <RefreshCw :size="16" />
                  保存并同步当前标的
                </el-button>
              </div>
            </section>
          </div>

          <div v-if="selected" class="instrument-detail">
            <div class="detail-head">
              <div>
                <p class="product-mark">{{ selected.ts_code }}</p>
                <h2>{{ selected.name }}</h2>
                <p class="subtle">
                  {{ typeLabel(selected.asset_type) }} · {{ selected.market || '市场未知' }} · 最近同步 {{ selected.last_synced_at || '暂无' }}
                </p>
              </div>
              <div class="detail-actions">
                <el-segmented v-model="freq" :options="freqOptions" @change="loadBars" />
                <el-button v-if="isAdmin" :loading="loading" @click="syncSelected">
                  <RefreshCw :size="16" />
                  同步
                </el-button>
              </div>
            </div>

            <div class="overview-grid">
              <div v-for="card in overviewCards" :key="card.key" class="stat-box">
                <span>{{ card.label }}</span>
                <strong>{{ card.value }}</strong>
                <small>{{ card.meta }}</small>
              </div>
            </div>

            <div class="research-grid">
              <section class="chart-panel">
                <div class="panel-title-row">
                  <div>
                    <h3>价格与指标</h3>
                    <p class="subtle">K线、均线、布林带、成交量与副图指标。</p>
                  </div>
                  <div class="layer-controls">
                    <el-checkbox-group v-model="priceLayers" @change="renderChart">
                      <el-checkbox-button label="ma5">MA5</el-checkbox-button>
                      <el-checkbox-button label="ma10">MA10</el-checkbox-button>
                      <el-checkbox-button label="ma20">MA20</el-checkbox-button>
                      <el-checkbox-button label="ma60">MA60</el-checkbox-button>
                      <el-checkbox-button label="boll">BOLL</el-checkbox-button>
                    </el-checkbox-group>
                    <el-segmented v-model="subChart" :options="subChartOptions" @change="renderChart" />
                  </div>
                </div>
                <div ref="chartRef" class="chart"></div>
              </section>

              <aside class="factor-panel">
                <div class="panel-title-row">
                  <div>
                    <h3>策略因子</h3>
                    <p class="subtle">仅展示当前计算值和历史分位，不给出结论。</p>
                  </div>
                </div>
                <div class="factor-groups">
                  <section v-for="group in factorGroups" :key="group.name" class="factor-group">
                    <h4>{{ group.name }}</h4>
                    <div class="factor-list">
                      <div v-for="factor in group.items" :key="factor.key" class="factor-row">
                        <div>
                          <span>{{ factor.label }}</span>
                          <strong>{{ factorValue(factor) }}</strong>
                        </div>
                        <div class="percentile">
                          <i :style="{ width: percentileWidth(factor.percentile) }"></i>
                          <em>{{ percentileText(factor.percentile) }}</em>
                        </div>
                      </div>
                    </div>
                  </section>
                </div>
              </aside>
            </div>

            <div class="data-grid">
              <section class="meta-panel">
                <h3>标的信息</h3>
                <dl>
                  <div>
                    <dt>行业</dt>
                    <dd>{{ selected.industry || '-' }}</dd>
                  </div>
                  <div>
                    <dt>地区</dt>
                    <dd>{{ selected.area || '-' }}</dd>
                  </div>
                  <div>
                    <dt>数据条数</dt>
                    <dd>{{ bars.length }}</dd>
                  </div>
                  <div>
                    <dt>处理模块</dt>
                    <dd>Market Engine</dd>
                  </div>
                </dl>
              </section>

              <section class="table-wrap">
                <div class="panel-title-row table-title">
                  <div>
                    <h3>最近行情</h3>
                    <p class="subtle">按交易日期倒序展示最近 80 条。</p>
                  </div>
                </div>
                <el-table :data="recentBars" height="340">
                  <el-table-column prop="trade_date" label="日期" width="120" />
                  <el-table-column prop="open" label="开盘" />
                  <el-table-column prop="high" label="最高" />
                  <el-table-column prop="low" label="最低" />
                  <el-table-column prop="close" label="收盘" />
                  <el-table-column prop="volume" label="成交量" />
                  <el-table-column prop="amount" label="成交额" />
                </el-table>
              </section>
            </div>
          </div>

          <div v-else class="empty-state">
            <Database :size="42" />
            <h2>选择一个标的开始研究</h2>
            <p>当前页面只展示管理员录入并发布的行情、指标和因子数据。</p>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { Database, KeyRound, LogIn, Plus, RefreshCw, Search } from '@lucide/vue'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const token = ref(localStorage.getItem('quant_lab_token') || '')
const user = ref(JSON.parse(localStorage.getItem('quant_lab_user') || 'null'))
const loading = ref(false)
const instruments = ref([])
const selected = ref(null)
const bars = ref([])
const analytics = ref({ overview: {}, factors: [], indicators: {} })
const indicators = ref({})
const dataSource = ref({
  provider: 'tushare',
  connection: { configured: false, token_masked: '', http_url: '', source: null, updated_at: null }
})
const dataSourceForm = ref({ tushare_token: '', tushare_http_url: 'https://tuaremax.top' })
const keyword = ref('')
const freq = ref('daily')
const chartRef = ref(null)
const priceLayers = ref(['ma5', 'ma10', 'ma20', 'boll'])
const subChart = ref('volume')
let chart

const loginForm = ref({ username: 'admin', password: '' })
const newInstrument = ref({ ts_code: '', asset_type: 'stock', data_start: '2018-01-01', data_end: '' })
const freqOptions = [
  { label: '日线', value: 'daily' },
  { label: '周线', value: 'weekly' }
]
const subChartOptions = [
  { label: '成交量', value: 'volume' },
  { label: 'RSI', value: 'rsi' },
  { label: 'MACD', value: 'macd' }
]

const isAdmin = computed(() => user.value?.role === 'admin')
const roleLabel = computed(() => (isAdmin.value ? '管理员' : '普通用户'))
const filteredInstruments = computed(() => {
  const key = keyword.value.trim().toLowerCase()
  if (!key) return instruments.value
  return instruments.value.filter((item) =>
    `${item.name} ${item.ts_code}`.toLowerCase().includes(key)
  )
})
const recentBars = computed(() => [...bars.value].reverse().slice(0, 80))
const overviewCards = computed(() => {
  const overview = analytics.value?.overview || {}
  return [
    { key: 'latest_close', label: '最新收盘', value: formatNumber(overview.latest_close), meta: freqLabel.value },
    { key: 'period_return_pct', label: '区间收益', value: formatPct(overview.period_return_pct), meta: '当前数据区间' },
    { key: 'return_20d_pct', label: '20期收益', value: formatPct(overview.return_20d_pct), meta: '滚动窗口' },
    { key: 'volatility_20d_pct', label: '20期波动率', value: formatPct(overview.volatility_20d_pct), meta: '年化估算' },
    { key: 'volume_ratio_20d', label: '量能倍率', value: formatUnit(overview.volume_ratio_20d, 'x'), meta: '相对20期均量' },
    { key: 'max_drawdown_pct', label: '最大回撤', value: formatPct(overview.max_drawdown_pct), meta: '当前数据区间' }
  ]
})
const factorGroups = computed(() => {
  const groups = new Map()
  for (const factor of analytics.value?.factors || []) {
    if (!groups.has(factor.group)) groups.set(factor.group, [])
    groups.get(factor.group).push(factor)
  }
  return [...groups.entries()].map(([name, items]) => ({ name, items }))
})
const freqLabel = computed(() => (freq.value === 'daily' ? '日线' : '周线'))

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
      ...(options.headers || {})
    }
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.message || data.error || '请求失败')
  }
  return data
}

async function login() {
  loading.value = true
  try {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(loginForm.value)
    })
    token.value = data.token
    user.value = data.user
    localStorage.setItem('quant_lab_token', data.token)
    localStorage.setItem('quant_lab_user', JSON.stringify(data.user))
    await loadInstruments()
    await loadDataSource()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

function logout() {
  token.value = ''
  user.value = null
  selected.value = null
  dataSource.value = {
    provider: 'tushare',
    connection: { configured: false, token_masked: '', http_url: '', source: null, updated_at: null }
  }
  dataSourceForm.value.tushare_token = ''
  dataSourceForm.value.tushare_http_url = 'https://tuaremax.top'
  localStorage.removeItem('quant_lab_token')
  localStorage.removeItem('quant_lab_user')
}

async function loadDataSource() {
  if (!token.value || !isAdmin.value) return
  try {
    dataSource.value = await request('/admin/data-source')
    dataSourceForm.value.tushare_http_url = dataSource.value.connection?.http_url || 'https://tuaremax.top'
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function saveDataSource(options = {}) {
  if (!isAdmin.value) return false
  const tokenValue = dataSourceForm.value.tushare_token.trim()
  const httpUrlValue = dataSourceForm.value.tushare_http_url.trim()
  if (!tokenValue && !httpUrlValue) {
    ElMessage.error('请先填写 Tushare Token 或接口地址')
    return false
  }
  loading.value = true
  try {
    const payload = {}
    if (tokenValue) payload.tushare_token = tokenValue
    if (httpUrlValue) payload.tushare_http_url = httpUrlValue
    dataSource.value = await request('/admin/data-source', {
      method: 'PATCH',
      body: JSON.stringify(payload)
    })
    dataSourceForm.value.tushare_token = ''
    dataSourceForm.value.tushare_http_url = dataSource.value.connection?.http_url || httpUrlValue
    if (!options.silent) ElMessage.success('Tushare 接口已保存')
    return true
  } catch (error) {
    ElMessage.error(error.message)
    return false
  } finally {
    loading.value = false
  }
}

async function saveAndSyncSelected() {
  if (!selected.value) {
    ElMessage.error('请先选择一个标的')
    return
  }
  const saved = await saveDataSource({ silent: true })
  if (!saved) return
  const synced = await syncSelected({ silent: true })
  if (synced) ElMessage.success('接口已保存，当前标的数据已同步')
}

async function loadInstruments() {
  if (!token.value) return
  loading.value = true
  try {
    const data = await request('/instruments')
    instruments.value = data.instruments
    if (!selected.value && instruments.value.length) {
      await selectInstrument(instruments.value[0])
    }
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function selectInstrument(item) {
  selected.value = item
  await loadBars()
}

async function loadBars() {
  if (!selected.value) return
  try {
    const [barData, analyticsData] = await Promise.all([
      request(`/instruments/${selected.value.id}/bars?freq=${freq.value}`),
      request(`/instruments/${selected.value.id}/analytics?freq=${freq.value}`)
    ])
    bars.value = barData.bars
    analytics.value = analyticsData
    indicators.value = analyticsData.indicators || {}
    await nextTick()
    renderChart()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function createAndSync() {
  loading.value = true
  try {
    const data = await request('/admin/instruments', {
      method: 'POST',
      body: JSON.stringify(newInstrument.value)
    })
    selected.value = data.instrument
    await request(`/admin/instruments/${data.instrument.id}/sync`, {
      method: 'POST',
      body: JSON.stringify({ end_date: newInstrument.value.data_end || '' })
    })
    await loadInstruments()
    await selectInstrument(data.instrument)
    ElMessage.success('标的已同步')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function syncSelected(options = {}) {
  if (!selected.value) return false
  loading.value = true
  try {
    await request(`/admin/instruments/${selected.value.id}/sync`, { method: 'POST' })
    await loadInstruments()
    await loadBars()
    if (!options.silent) ElMessage.success('同步完成')
    return true
  } catch (error) {
    ElMessage.error(error.message)
    return false
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!chartRef.value) return
  chart = chart || echarts.init(chartRef.value)
  const dates = bars.value.map((item) => item.trade_date)
  const candle = bars.value.map((item) => [item.open, item.close, item.low, item.high])
  const volume = bars.value.map((item) => item.volume)
  const series = [
    {
      name: 'K线',
      type: 'candlestick',
      data: candle,
      itemStyle: { color: '#d85a4a', color0: '#2f7d5b', borderColor: '#d85a4a', borderColor0: '#2f7d5b' }
    }
  ]

  addPriceLayer(series, 'ma5', 'MA5', '#4d7ea8')
  addPriceLayer(series, 'ma10', 'MA10', '#b7791f')
  addPriceLayer(series, 'ma20', 'MA20', '#2f7d5b')
  addPriceLayer(series, 'ma60', 'MA60', '#6b5b95')
  if (priceLayers.value.includes('boll')) {
    series.push(lineSeries('BOLL上轨', indicators.value?.boll?.upper || [], '#8b8f9a', 'dashed'))
    series.push(lineSeries('BOLL中轨', indicators.value?.boll?.mid || [], '#59656f', 'dotted'))
    series.push(lineSeries('BOLL下轨', indicators.value?.boll?.lower || [], '#8b8f9a', 'dashed'))
  }

  const legend = series.map((item) => item.name)
  const yAxis = [{ scale: true, splitLine: { lineStyle: { color: '#eef1ec' } } }]
  const xAxis = [{ type: 'category', data: dates, scale: true, boundaryGap: false, axisLine: { lineStyle: { color: '#cbd6ce' } } }]
  const grid = [{ left: 70, right: 24, top: 44, height: 292 }]

  grid.push({ left: 70, right: 24, top: 372, height: subChart.value === 'volume' ? 104 : 72 })
  xAxis.push({ type: 'category', data: dates, gridIndex: 1, scale: true, boundaryGap: false, axisLabel: { show: subChart.value === 'volume' } })
  yAxis.push({
    gridIndex: 1,
    scale: true,
    axisLabel: { formatter: compactAxisNumber, margin: 8 },
    splitLine: { lineStyle: { color: '#eef1ec' } }
  })
  series.push({ name: '成交量', type: 'bar', data: volume, xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: '#b7c5bd' } })
  legend.push('成交量')

  if (subChart.value !== 'volume') {
    grid.push({ left: 70, right: 24, top: 478, height: 96 })
    xAxis.push({ type: 'category', data: dates, gridIndex: 2, scale: true, boundaryGap: false })
    yAxis.push({ gridIndex: 2, scale: true, splitLine: { lineStyle: { color: '#eef1ec' } } })
    if (subChart.value === 'rsi') {
      series.push({ ...lineSeries('RSI14', indicators.value?.rsi14 || [], '#a35f2d'), xAxisIndex: 2, yAxisIndex: 2 })
      legend.push('RSI14')
    }
    if (subChart.value === 'macd') {
      const macd = indicators.value?.macd || {}
      series.push({ name: 'MACD', type: 'bar', data: macd.macd || [], xAxisIndex: 2, yAxisIndex: 2, itemStyle: { color: '#8ea89a' } })
      series.push({ ...lineSeries('DIF', macd.dif || [], '#4d7ea8'), xAxisIndex: 2, yAxisIndex: 2 })
      series.push({ ...lineSeries('DEA', macd.dea || [], '#b7791f'), xAxisIndex: 2, yAxisIndex: 2 })
      legend.push('MACD', 'DIF', 'DEA')
    }
  }

  chart.setOption({
    animation: false,
    backgroundColor: '#ffffff',
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: legend, top: 8, textStyle: { color: '#425047' } },
    grid,
    xAxis,
    yAxis,
    dataZoom: [{ type: 'inside', xAxisIndex: xAxis.map((_, index) => index) }, { show: true, xAxisIndex: xAxis.map((_, index) => index), bottom: 8 }],
    series
  }, true)
}

function addPriceLayer(series, key, name, color) {
  if (priceLayers.value.includes(key)) {
    series.push(lineSeries(name, indicators.value?.[key] || [], color))
  }
}

function lineSeries(name, data, color, type = 'solid') {
  return {
    name,
    type: 'line',
    data,
    smooth: true,
    showSymbol: false,
    lineStyle: { width: 1.5, color, type }
  }
}

function typeLabel(type) {
  return { stock: '股票', etf: 'ETF', fund: '基金' }[type] || type
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: digits })
}

function compactAxisNumber(value) {
  const number = Number(value)
  if (Number.isNaN(number)) return '-'
  const abs = Math.abs(number)
  if (abs >= 100000000) return `${trimNumber(number / 100000000)}亿`
  if (abs >= 10000) return `${trimNumber(number / 10000)}万`
  return trimNumber(number)
}

function trimNumber(value) {
  return Number(value.toFixed(2)).toLocaleString('zh-CN')
}

function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  return `${Number(value).toFixed(2)}%`
}

function formatUnit(value, unit) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  return `${Number(value).toFixed(2)}${unit}`
}

function factorValue(factor) {
  if (factor.value === null || factor.value === undefined || Number.isNaN(Number(factor.value))) return '-'
  if (factor.unit === '%') return formatPct(factor.value)
  if (factor.unit === 'x') return formatUnit(factor.value, 'x')
  return formatNumber(factor.value)
}

function percentileWidth(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '0%'
  return `${Math.max(0, Math.min(100, Number(value)))}%`
}

function percentileText(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '无分位'
  return `P${Number(value).toFixed(1)}`
}

const resizeChart = () => chart?.resize()
window.addEventListener('resize', resizeChart)
onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
})

if (token.value) {
  loadInstruments()
  loadDataSource()
}
</script>

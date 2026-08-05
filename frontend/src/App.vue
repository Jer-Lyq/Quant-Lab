<template>
  <main class="app-shell">
    <section v-if="!token" class="login-screen">
      <div class="login-panel">
        <div>
          <p class="eyebrow">Quant Lab</p>
          <h1>量化研究数据工作台</h1>
          <p class="subtle">登录后查看已录入标的，管理员可以通过 Tushare 同步学习数据。</p>
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
          <p class="eyebrow">Quant Lab</p>
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
            <el-button circle :loading="loading" @click="loadInstruments">
              <RefreshCw :size="16" />
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
          <div v-if="isAdmin" class="admin-panel">
            <h2>管理员录入</h2>
            <div class="admin-grid">
              <el-input v-model="newInstrument.ts_code" placeholder="例如 000001.SZ" />
              <el-select v-model="newInstrument.asset_type">
                <el-option label="股票" value="stock" />
                <el-option label="ETF" value="etf" />
                <el-option label="基金" value="fund" />
              </el-select>
              <el-date-picker v-model="newInstrument.data_start" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" />
              <el-date-picker v-model="newInstrument.data_end" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" />
              <el-button type="primary" :loading="loading" @click="createAndSync">
                <Plus :size="16" />
                新增并同步
              </el-button>
            </div>
          </div>

          <div v-if="selected" class="instrument-detail">
            <div class="detail-head">
              <div>
                <h2>{{ selected.name }}</h2>
                <p class="subtle">
                  {{ selected.ts_code }} · {{ typeLabel(selected.asset_type) }} · 最近同步 {{ selected.last_synced_at || '暂无' }}
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

            <div class="stats-row">
              <div class="stat-box">
                <span>市场</span>
                <strong>{{ selected.market || '-' }}</strong>
              </div>
              <div class="stat-box">
                <span>行业</span>
                <strong>{{ selected.industry || '-' }}</strong>
              </div>
              <div class="stat-box">
                <span>地区</span>
                <strong>{{ selected.area || '-' }}</strong>
              </div>
              <div class="stat-box">
                <span>数据条数</span>
                <strong>{{ bars.length }}</strong>
              </div>
            </div>

            <div ref="chartRef" class="chart"></div>

            <div class="table-wrap">
              <el-table :data="recentBars" height="300">
                <el-table-column prop="trade_date" label="日期" width="120" />
                <el-table-column prop="open" label="开盘" />
                <el-table-column prop="high" label="最高" />
                <el-table-column prop="low" label="最低" />
                <el-table-column prop="close" label="收盘" />
                <el-table-column prop="volume" label="成交量" />
              </el-table>
            </div>
          </div>

          <div v-else class="empty-state">
            <Database :size="42" />
            <h2>选择一个标的开始研究</h2>
            <p>首版数据中心只展示管理员录入并发布的少量学习标的。</p>
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
import { Database, LogIn, Plus, RefreshCw, Search } from '@lucide/vue'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const token = ref(localStorage.getItem('quant_lab_token') || '')
const user = ref(JSON.parse(localStorage.getItem('quant_lab_user') || 'null'))
const loading = ref(false)
const instruments = ref([])
const selected = ref(null)
const bars = ref([])
const indicators = ref(null)
const keyword = ref('')
const freq = ref('daily')
const chartRef = ref(null)
let chart

const loginForm = ref({ username: 'admin', password: '' })
const newInstrument = ref({ ts_code: '', asset_type: 'stock', data_start: '2018-01-01', data_end: '' })
const freqOptions = [
  { label: '日线', value: 'daily' },
  { label: '周线', value: 'weekly' }
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
  localStorage.removeItem('quant_lab_token')
  localStorage.removeItem('quant_lab_user')
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
  const [barData, indicatorData] = await Promise.all([
    request(`/instruments/${selected.value.id}/bars?freq=${freq.value}`),
    request(`/instruments/${selected.value.id}/indicators?freq=${freq.value}`)
  ])
  bars.value = barData.bars
  indicators.value = indicatorData.indicators
  await nextTick()
  renderChart()
}

async function createAndSync() {
  loading.value = true
  try {
    const data = await request('/admin/instruments', {
      method: 'POST',
      body: JSON.stringify(newInstrument.value)
    })
    selected.value = data.instrument
    await request(`/admin/instruments/${data.instrument.id}/sync`, { method: 'POST' })
    await loadInstruments()
    await selectInstrument(data.instrument)
    ElMessage.success('标的已同步')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function syncSelected() {
  if (!selected.value) return
  loading.value = true
  try {
    await request(`/admin/instruments/${selected.value.id}/sync`, { method: 'POST' })
    await loadInstruments()
    await loadBars()
    ElMessage.success('同步完成')
  } catch (error) {
    ElMessage.error(error.message)
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
  chart.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { data: ['K线', 'MA5', 'MA10', 'MA20', '成交量'] },
    grid: [
      { left: 50, right: 24, top: 40, height: 280 },
      { left: 50, right: 24, top: 360, height: 100 }
    ],
    xAxis: [
      { type: 'category', data: dates, scale: true, boundaryGap: false },
      { type: 'category', data: dates, gridIndex: 1, scale: true, boundaryGap: false }
    ],
    yAxis: [{ scale: true }, { gridIndex: 1, scale: true }],
    dataZoom: [{ type: 'inside' }, { show: true, xAxisIndex: [0, 1], bottom: 8 }],
    series: [
      { name: 'K线', type: 'candlestick', data: candle },
      { name: 'MA5', type: 'line', data: indicators.value?.ma5 || [], smooth: true, showSymbol: false },
      { name: 'MA10', type: 'line', data: indicators.value?.ma10 || [], smooth: true, showSymbol: false },
      { name: 'MA20', type: 'line', data: indicators.value?.ma20 || [], smooth: true, showSymbol: false },
      { name: '成交量', type: 'bar', data: volume, xAxisIndex: 1, yAxisIndex: 1 }
    ]
  })
}

function typeLabel(type) {
  return { stock: '股票', etf: 'ETF', fund: '基金' }[type] || type
}

const resizeChart = () => chart?.resize()
window.addEventListener('resize', resizeChart)
onBeforeUnmount(() => chart?.dispose())

if (token.value) {
  loadInstruments()
}
</script>

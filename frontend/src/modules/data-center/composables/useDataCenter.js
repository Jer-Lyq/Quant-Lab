import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiRequest } from '../../../app/apiClient'
import {
  createDefaultAnalytics,
  createDefaultDataSource,
  createDefaultDataSourceForm,
  createDefaultInstrumentForm
} from '../utils/labels'
import { formatNumber, formatPct, formatUnit } from '../utils/formatters'

export function useDataCenter(tokenRef, userRef) {
  const loading = ref(false)
  const instruments = ref([])
  const selected = ref(null)
  const bars = ref([])
  const analytics = ref(createDefaultAnalytics())
  const indicators = ref({})
  const dataSource = ref(createDefaultDataSource())
  const dataSourceForm = ref(createDefaultDataSourceForm())
  const keyword = ref('')
  const freq = ref('daily')
  const priceLayers = ref(['ma5', 'ma10', 'ma20', 'boll'])
  const subChart = ref('volume')
  const newInstrument = ref(createDefaultInstrumentForm())

  const isAdmin = computed(() => userRef.value?.role === 'admin')
  const filteredInstruments = computed(() => {
    const key = keyword.value.trim().toLowerCase()
    if (!key) return instruments.value
    return instruments.value.filter((item) =>
      `${item.name} ${item.ts_code}`.toLowerCase().includes(key)
    )
  })
  const recentBars = computed(() => [...bars.value].reverse().slice(0, 80))
  const freqLabel = computed(() => (freq.value === 'daily' ? '日线' : '周线'))
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

  async function request(path, options = {}) {
    return apiRequest(path, {
      ...options,
      token: tokenRef.value
    })
  }

  function clearSelectedData() {
    selected.value = null
    bars.value = []
    analytics.value = createDefaultAnalytics()
    indicators.value = {}
  }

  async function loadDataSource() {
    if (!tokenRef.value || !isAdmin.value) return
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
    if (!tokenRef.value) return
    loading.value = true
    try {
      const data = await request('/instruments')
      instruments.value = data.instruments
      const current = selected.value
        ? instruments.value.find((item) => item.id === selected.value.id)
        : null
      if (current) {
        selected.value = current
      } else if (instruments.value.length) {
        await selectInstrument(instruments.value[0])
      } else {
        clearSelectedData()
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

  async function deleteInstrument(item) {
    if (!isAdmin.value || !item) return
    try {
      await ElMessageBox.confirm(
        `删除 ${item.name}（${item.ts_code}）会同时删除这个标的的行情文件、指标缓存和同步诊断数据。`,
        '删除标的',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger'
        }
      )
    } catch {
      return
    }

    loading.value = true
    try {
      await request(`/admin/instruments/${item.id}`, { method: 'DELETE' })
      if (selected.value?.id === item.id) {
        clearSelectedData()
      }
      await loadInstruments()
      ElMessage.success('标的及相关数据已删除')
    } catch (error) {
      ElMessage.error(error.message)
    } finally {
      loading.value = false
    }
  }

  loadInstruments()
  loadDataSource()

  return {
    loading,
    instruments,
    selected,
    bars,
    analytics,
    indicators,
    dataSource,
    dataSourceForm,
    keyword,
    freq,
    priceLayers,
    subChart,
    newInstrument,
    isAdmin,
    filteredInstruments,
    recentBars,
    overviewCards,
    factorGroups,
    loadInstruments,
    selectInstrument,
    loadBars,
    createAndSync,
    syncSelected,
    deleteInstrument,
    loadDataSource,
    saveDataSource,
    saveAndSyncSelected
  }
}

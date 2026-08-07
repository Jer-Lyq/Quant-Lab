import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { apiRequest } from '../../../app/apiClient'
import { activeBacktestStatuses } from '../utils/labels'


const ERROR_MESSAGES = {
  adjustment_factor_required: '该股票缺少复权因子，请在数据中心重新同步后再回测。',
  backtest_cancel_denied: '只能取消自己创建的任务。',
  backtest_data_incomplete: '所选区间存在不完整行情，请先检查数据。',
  backtest_data_insufficient: '所选区间行情不足，至少需要两个交易日。',
  backtest_operation_failed: '回测操作失败，请刷新后重试。',
  discarded_strategy_read_only: '废弃策略不能创建新回测。',
  incomplete_adjustment_factor: '所选区间的复权因子不完整，请重新同步行情。',
  invalid_backtest_date_range: '结束日期必须晚于开始日期。',
  rqalpha_bundle_missing: '服务器尚未准备 RQAlpha 数据包。',
  strategy_instrument_required: '只能回测该策略已经关联的标的。',
  strategy_version_invalid: '请选择校验通过的代码版本。',
  unsupported_backtest_asset_type: '首版仅支持股票和 ETF。',
  unsupported_backtest_frequency: '首版仅支持日线回测。'
}


function errorMessage(error) {
  return ERROR_MESSAGES[error.code] || error.message || '回测操作失败'
}


export function useBacktests(tokenRef, targetRef) {
  const loading = ref(false)
  const submitting = ref(false)
  const options = ref({ strategy: null, versions: [], instruments: [], defaults: {} })
  const runs = ref([])
  const selectedRun = ref(null)
  const artifacts = ref({})
  const form = reactive({
    strategy_version_id: null,
    instrument_id: null,
    date_range: [],
    initial_cash: 1_000_000,
    commission_rate: 0.0003,
    slippage_rate: 0.0001,
    adjustment_mode: 'qfq',
    benchmark: ''
  })
  let pollTimer = null
  let loadEpoch = 0

  const strategy = computed(() => options.value.strategy || targetRef.value?.strategy || null)
  const selectedInstrument = computed(
    () => options.value.instruments.find((item) => item.id === form.instrument_id) || null
  )
  const canCreate = computed(() => {
    return Boolean(
      strategy.value &&
      form.strategy_version_id &&
      form.instrument_id &&
      form.date_range?.length === 2 &&
      !submitting.value
    )
  })
  const hasActiveRuns = computed(() => runs.value.some((run) => activeBacktestStatuses.has(run.status)))

  async function request(path, requestOptions = {}) {
    return apiRequest(path, { ...requestOptions, token: tokenRef.value })
  }

  function applyDefaults(data) {
    const validVersions = (data.versions || []).filter((item) => item.validation_status === 'valid')
    const availableInstruments = (data.instruments || []).filter(
      (item) => item.backtest_supported && item.bar_count >= 2
    )
    form.strategy_version_id = validVersions[0]?.id || null
    form.instrument_id = availableInstruments[0]?.id || null
    form.initial_cash = data.defaults?.initial_cash ?? 1_000_000
    form.commission_rate = data.defaults?.commission_rate ?? 0.0003
    form.slippage_rate = data.defaults?.slippage_rate ?? 0.0001
    form.adjustment_mode = data.defaults?.adjustment_mode || 'qfq'
    applyInstrumentDates(availableInstruments[0])
  }

  function applyInstrumentDates(instrument = selectedInstrument.value) {
    form.date_range = instrument?.data_start && instrument?.data_end
      ? [instrument.data_start, instrument.data_end]
      : []
  }

  async function loadOptions(strategyId) {
    if (!strategyId) {
      options.value = { strategy: null, versions: [], instruments: [], defaults: {} }
      return
    }
    const data = await request(`/backtests/options?strategy_id=${strategyId}`)
    options.value = data
    applyDefaults(data)
  }

  async function loadRuns({ keepSelection = true } = {}) {
    if (!tokenRef.value) return
    const epoch = ++loadEpoch
    const strategyId = targetRef.value?.strategy?.id
    const query = strategyId ? `?strategy_id=${strategyId}` : ''
    try {
      const data = await request(`/backtests${query}`)
      if (epoch !== loadEpoch) return
      runs.value = data.backtests || []
      if (selectedRun.value && keepSelection) {
        const current = runs.value.find((item) => item.id === selectedRun.value.id)
        if (current) {
          selectedRun.value = current
          if (current.status === 'success' && !Object.keys(artifacts.value).length) {
            await loadArtifacts(current.id)
          }
        }
      } else if (runs.value.length) {
        await selectRun(runs.value[0])
      } else {
        selectedRun.value = null
        artifacts.value = {}
      }
      syncPolling()
    } catch (error) {
      ElMessage.error(errorMessage(error))
    }
  }

  async function selectRun(run) {
    if (!run) return
    selectedRun.value = run
    artifacts.value = {}
    try {
      const data = await request(`/backtests/${run.id}`)
      selectedRun.value = data.backtest
      if (data.backtest.status === 'success') await loadArtifacts(run.id)
    } catch (error) {
      ElMessage.error(errorMessage(error))
    }
  }

  async function loadArtifacts(runId) {
    try {
      const data = await request(`/backtests/${runId}/artifacts`)
      artifacts.value = data.artifacts || {}
    } catch (error) {
      ElMessage.error(errorMessage(error))
    }
  }

  async function createRun() {
    if (!canCreate.value) return
    submitting.value = true
    try {
      const data = await request('/backtests', {
        method: 'POST',
        body: JSON.stringify({
          strategy_id: strategy.value.id,
          strategy_version_id: form.strategy_version_id,
          instrument_id: form.instrument_id,
          start_date: form.date_range[0],
          end_date: form.date_range[1],
          initial_cash: Number(form.initial_cash),
          commission_rate: Number(form.commission_rate),
          slippage_rate: Number(form.slippage_rate),
          adjustment_mode: form.adjustment_mode,
          benchmark: form.benchmark.trim() || null,
          freq: 'daily'
        })
      })
      selectedRun.value = data.backtest
      artifacts.value = {}
      await loadRuns()
      ElMessage.success('回测任务已进入队列')
    } catch (error) {
      ElMessage.error(errorMessage(error))
    } finally {
      submitting.value = false
    }
  }

  async function cancelRun(run = selectedRun.value) {
    if (!run || !activeBacktestStatuses.has(run.status)) return
    try {
      const data = await request(`/backtests/${run.id}/cancel`, { method: 'POST' })
      selectedRun.value = data.backtest
      await loadRuns()
      ElMessage.success(data.backtest.status === 'cancelled' ? '任务已取消' : '已提交取消请求')
    } catch (error) {
      ElMessage.error(errorMessage(error))
    }
  }

  function syncPolling() {
    if (hasActiveRuns.value && !pollTimer) {
      pollTimer = window.setInterval(() => loadRuns(), 2000)
    } else if (!hasActiveRuns.value && pollTimer) {
      window.clearInterval(pollTimer)
      pollTimer = null
    }
  }

  async function initialize() {
    if (!tokenRef.value) return
    loading.value = true
    try {
      await loadOptions(targetRef.value?.strategy?.id)
      await loadRuns({ keepSelection: false })
    } catch (error) {
      ElMessage.error(errorMessage(error))
    } finally {
      loading.value = false
    }
  }

  watch(() => form.instrument_id, () => applyInstrumentDates())
  watch([tokenRef, targetRef], initialize, { immediate: true, deep: true })
  onBeforeUnmount(() => {
    if (pollTimer) window.clearInterval(pollTimer)
  })

  return {
    loading,
    submitting,
    options,
    runs,
    selectedRun,
    artifacts,
    form,
    strategy,
    selectedInstrument,
    canCreate,
    loadRuns,
    selectRun,
    createRun,
    cancelRun
  }
}

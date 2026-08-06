import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiRequest } from '../../../app/apiClient'
import { createDefaultStrategyForm, createDefaultVersionForm } from '../utils/labels'

const ERROR_MESSAGES = {
  discarded_strategy_read_only: '废弃策略为只读状态，请先恢复为草稿后再修改版本或标的。',
  invalid_instrument_id: '标的参数无效。',
  json_object_required: '请求数据格式无效，请刷新页面后重试。',
  request_too_large: '提交内容过大，请缩短策略说明或代码。',
  new_strategy_must_start_as_draft: '新策略必须先以草稿状态创建。',
  strategy_backtest_in_progress: '策略正在回测，暂时不能修改代码版本或关联标的。',
  strategy_code_required: '策略代码不能为空。',
  strategy_code_too_long: '策略代码超过长度限制。',
  strategy_database_conflict: '策略数据发生冲突，请刷新后重试。',
  strategy_has_backtest_history: '该策略已有回测历史，不能直接删除。',
  strategy_name_required: '请填写策略名称。',
  strategy_name_too_long: '策略名称不能超过 120 个字符。',
  strategy_operation_failed: '策略操作失败，请刷新后重试。',
  strategy_status_transition_denied: '该状态只能由管理员或回测流程维护。',
  strategy_valid_version_required: '进入待回测或已验证状态前，需要先保存一个校验通过的代码版本。',
  system_managed_strategy_read_only: '回测中或已验证策略由系统维护，请联系管理员先退回草稿。',
  strategy_version_in_use: '该版本已有回测记录，不能删除。',
  strategy_version_name_exists: '版本名称已存在，请使用新的版本名称。',
  version_name_too_long: '版本名称不能超过 80 个字符。'
}

function errorMessage(error) {
  return ERROR_MESSAGES[error.code] || error.message || '策略操作失败'
}

export function useStrategies(tokenRef, userRef) {
  const loading = ref(false)
  const saving = ref(false)
  const strategies = ref([])
  const selected = ref(null)
  const versions = ref([])
  const linkedInstruments = ref([])
  const instruments = ref([])
  const keyword = ref('')
  const statusFilter = ref('')
  const typeFilter = ref('')
  const editorForm = reactive(createDefaultStrategyForm())
  const versionForm = reactive(createDefaultVersionForm())
  const createDialogVisible = ref(false)
  const createForm = reactive(createDefaultStrategyForm())
  let selectionEpoch = 0

  const canEdit = computed(() => {
    if (!selected.value || !userRef.value) return false
    if (userRef.value.role === 'admin') return true
    if (['backtesting', 'validated'].includes(selected.value.status)) return false
    return selected.value.author_id === userRef.value.id
  })

  const filteredStrategies = computed(() => {
    const key = keyword.value.trim().toLowerCase()
    return strategies.value.filter((item) => {
      const text = `${item.name} ${item.strategy_idea || ''} ${item.description || ''} ${item.author_name || ''}`.toLowerCase()
      const matchesKeyword = !key || text.includes(key)
      const matchesStatus = !statusFilter.value || item.status === statusFilter.value
      const matchesType = !typeFilter.value || item.strategy_type === typeFilter.value
      return matchesKeyword && matchesStatus && matchesType
    })
  })

  const availableInstruments = computed(() => {
    const linkedIds = new Set(linkedInstruments.value.map((item) => item.id))
    return instruments.value.filter((item) => !linkedIds.has(item.id))
  })

  async function request(path, options = {}) {
    return apiRequest(path, {
      ...options,
      token: tokenRef.value
    })
  }

  function resetStrategyForm(target) {
    Object.assign(target, createDefaultStrategyForm())
  }

  function applyStrategyForm(strategy) {
    Object.assign(editorForm, {
      name: strategy?.name || '',
      description: strategy?.description || '',
      strategy_idea: strategy?.strategy_idea || '',
      uploader_notes: strategy?.uploader_notes || '',
      strategy_type: strategy?.strategy_type || 'custom',
      market: strategy?.market || 'A股',
      freq: strategy?.freq || 'daily',
      status: strategy?.status || 'draft'
    })
  }

  function applyVersionForm(version, fallbackCode = '') {
    Object.assign(versionForm, {
      version_name: '',
      notes: '',
      code: version?.code || fallbackCode || createDefaultVersionForm().code
    })
  }

  async function loadStrategies(options = {}) {
    if (!tokenRef.value) return
    loading.value = true
    try {
      const data = await request('/strategies')
      strategies.value = data.strategies || []
      if (selected.value && !options.reloadSelected) {
        const current = strategies.value.find((item) => item.id === selected.value.id)
        if (current) selected.value = { ...selected.value, ...current }
      } else if (selected.value) {
        const current = strategies.value.find((item) => item.id === selected.value.id)
        if (current) {
          await selectStrategy(current)
        } else if (strategies.value.length) {
          await selectStrategy(strategies.value[0])
        } else {
          clearSelected()
        }
      } else if (strategies.value.length) {
        await selectStrategy(strategies.value[0])
      }
    } catch (error) {
      ElMessage.error(errorMessage(error))
    } finally {
      loading.value = false
    }
  }

  async function loadInstruments() {
    if (!tokenRef.value) return
    try {
      const data = await request('/instruments')
      instruments.value = data.instruments || []
    } catch (error) {
      ElMessage.error(errorMessage(error))
    }
  }

  function clearSelected() {
    selectionEpoch += 1
    selected.value = null
    versions.value = []
    linkedInstruments.value = []
    applyStrategyForm(null)
    applyVersionForm(null)
  }

  async function selectStrategy(item) {
    if (!item) {
      clearSelected()
      return
    }
    const currentEpoch = ++selectionEpoch
    loading.value = true
    try {
      const data = await request(`/strategies/${item.id}`)
      if (currentEpoch !== selectionEpoch) return
      selected.value = data.strategy
      const versionList = data.versions || []
      versions.value = data.latest_version
        ? versionList.map((version) => version.id === data.latest_version.id ? data.latest_version : version)
        : versionList
      linkedInstruments.value = data.instruments || []
      applyStrategyForm(data.strategy)
      applyVersionForm(data.latest_version, data.default_code)
    } catch (error) {
      if (currentEpoch === selectionEpoch) ElMessage.error(errorMessage(error))
    } finally {
      if (currentEpoch === selectionEpoch) loading.value = false
    }
  }

  async function loadVersion(version) {
    if (!version || version.code !== undefined) return version
    try {
      const data = await request(`/strategy-versions/${version.id}`)
      const loaded = data.version
      versions.value = versions.value.map((item) => item.id === loaded.id ? loaded : item)
      return loaded
    } catch (error) {
      ElMessage.error(errorMessage(error))
      return null
    }
  }

  async function createStrategy() {
    saving.value = true
    try {
      const data = await request('/strategies', {
        method: 'POST',
        body: JSON.stringify(createForm)
      })
      createDialogVisible.value = false
      resetStrategyForm(createForm)
      await loadStrategies({ reloadSelected: true })
      await selectStrategy(data.strategy)
      ElMessage.success('策略已创建')
    } catch (error) {
      ElMessage.error(errorMessage(error))
    } finally {
      saving.value = false
    }
  }

  async function saveStrategy() {
    if (!selected.value || !canEdit.value) return
    saving.value = true
    try {
      const data = await request(`/strategies/${selected.value.id}`, {
        method: 'PATCH',
        body: JSON.stringify(editorForm)
      })
      selected.value = data.strategy
      applyStrategyForm(data.strategy)
      await loadStrategies()
      ElMessage.success('策略属性已保存')
    } catch (error) {
      ElMessage.error(errorMessage(error))
    } finally {
      saving.value = false
    }
  }

  async function saveVersion() {
    if (!selected.value || !canEdit.value) return
    saving.value = true
    try {
      const data = await request(`/strategies/${selected.value.id}/versions`, {
        method: 'POST',
        body: JSON.stringify(versionForm)
      })
      versions.value = [data.version, ...versions.value]
      versionForm.version_name = ''
      versionForm.notes = ''
      await loadStrategies()
      ElMessage.success(
        data.version.validation_status === 'valid'
          ? '代码版本已保存，结构校验通过'
          : `代码版本已保存：${data.version.validation_message}`
      )
    } catch (error) {
      ElMessage.error(errorMessage(error))
    } finally {
      saving.value = false
    }
  }

  async function deleteVersion(version) {
    if (!selected.value || !version || !canEdit.value) return
    try {
      await ElMessageBox.confirm(
        `删除代码版本「${version.version_name}」后无法恢复。已被回测引用的版本不会被删除。`,
        '删除代码版本',
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

    saving.value = true
    try {
      await request(`/strategies/${selected.value.id}/versions/${version.id}`, { method: 'DELETE' })
      versions.value = versions.value.filter((item) => item.id !== version.id)
      if (versionForm.code === version.code) {
        applyVersionForm(versions.value[0])
      }
      await loadStrategies()
      ElMessage.success('代码版本已删除')
    } catch (error) {
      ElMessage.error(errorMessage(error))
    } finally {
      saving.value = false
    }
  }

  async function deleteStrategy(item) {
    if (!item) return
    try {
      await ElMessageBox.confirm(`删除策略「${item.name}」会同时删除它的代码版本和关联关系。`, '删除策略', {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      })
    } catch {
      return
    }

    loading.value = true
    try {
      await request(`/strategies/${item.id}`, { method: 'DELETE' })
      if (selected.value?.id === item.id) clearSelected()
      await loadStrategies()
      ElMessage.success('策略已删除')
    } catch (error) {
      ElMessage.error(errorMessage(error))
    } finally {
      loading.value = false
    }
  }

  async function addInstrument(instrumentId) {
    if (!selected.value || !instrumentId || !canEdit.value) return
    try {
      const data = await request(`/strategies/${selected.value.id}/instruments`, {
        method: 'POST',
        body: JSON.stringify({ instrument_id: instrumentId })
      })
      linkedInstruments.value = data.instruments || []
      await loadStrategies()
      ElMessage.success('标的已关联')
    } catch (error) {
      ElMessage.error(errorMessage(error))
    }
  }

  async function removeInstrument(instrumentId) {
    if (!selected.value || !canEdit.value) return
    try {
      const data = await request(`/strategies/${selected.value.id}/instruments/${instrumentId}`, {
        method: 'DELETE'
      })
      linkedInstruments.value = data.instruments || []
      await loadStrategies()
      ElMessage.success('关联已移除')
    } catch (error) {
      ElMessage.error(errorMessage(error))
    }
  }

  async function useVersion(version) {
    const loaded = await loadVersion(version)
    if (!loaded) return
    applyVersionForm(loaded)
    ElMessage.info(`已载入 ${loaded.version_name} 的代码，可另存为新版本`)
  }

  loadStrategies()
  loadInstruments()

  return {
    loading,
    saving,
    strategies,
    selected,
    versions,
    linkedInstruments,
    instruments,
    keyword,
    statusFilter,
    typeFilter,
    editorForm,
    versionForm,
    createDialogVisible,
    createForm,
    canEdit,
    filteredStrategies,
    availableInstruments,
    loadStrategies,
    selectStrategy,
    loadVersion,
    createStrategy,
    saveStrategy,
    saveVersion,
    deleteVersion,
    deleteStrategy,
    addInstrument,
    removeInstrument,
    useVersion,
    resetStrategyForm
  }
}

import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiRequest } from '../../../app/apiClient'
import { createDefaultStrategyForm, createDefaultVersionForm } from '../utils/labels'

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

  const canEdit = computed(() => {
    if (!selected.value || !userRef.value) return false
    return userRef.value.role === 'admin' || selected.value.author_id === userRef.value.id
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
      ElMessage.error(error.message)
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
      ElMessage.error(error.message)
    }
  }

  function clearSelected() {
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
    loading.value = true
    try {
      const data = await request(`/strategies/${item.id}`)
      selected.value = data.strategy
      versions.value = data.versions || []
      linkedInstruments.value = data.instruments || []
      applyStrategyForm(data.strategy)
      applyVersionForm(versions.value[0], data.default_code)
    } catch (error) {
      ElMessage.error(error.message)
    } finally {
      loading.value = false
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
      ElMessage.error(error.message)
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
      ElMessage.error(error.message)
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
      ElMessage.error(error.message)
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
      const message = error.message === 'strategy_version_in_use'
        ? '该版本已有回测记录，不能删除'
        : error.message
      ElMessage.error(message)
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
      ElMessage.error(error.message)
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
      ElMessage.error(error.message)
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
      ElMessage.error(error.message)
    }
  }

  function useVersion(version) {
    applyVersionForm(version)
    ElMessage.info(`已载入 ${version.version_name} 的代码，可另存为新版本`)
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

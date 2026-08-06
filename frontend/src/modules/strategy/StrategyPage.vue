<template>
  <div class="layout strategy-layout">
    <StrategyList
      v-model:keyword="keyword"
      v-model:status-filter="statusFilter"
      v-model:type-filter="typeFilter"
      :strategies="filteredStrategies"
      :selected="selected"
      :loading="loading"
      :user="user"
      @refresh="loadStrategies"
      @create="openCreateDialog"
      @select="handleSelectStrategy"
      @delete="deleteStrategy"
    />

    <section class="content strategy-content">
      <StrategyEditor
        v-if="activeView === 'overview'"
        :strategy="selected"
        :editor-form="editorForm"
        :version-form="versionForm"
        :versions="versions"
        :can-edit="canEdit"
        :status-options="editableStatusOptions"
        :saving="saving"
        @save-strategy="saveStrategy"
        @save-version="saveVersion"
        @quick-backtest="openQuickBacktest"
        @open-history="openBacktestHistory"
        @open-versions="openVersionStudio"
        @open-instruments="openInstrumentStudio"
      />
      <StrategyVersionStudio
        v-else-if="activeView === 'versions'"
        :strategy="selected"
        :versions="versions"
        :selected-version="selectedVersion"
        :can-edit="canEdit"
        :saving="saving"
        @back="activeView = 'overview'"
        @save-version="saveVersion"
        @select-version="selectVersion"
        @use-version="useVersion"
        @delete-version="deleteVersion"
      />
      <StrategyInstrumentStudio
        v-else
        :strategy="selected"
        :linked-instruments="linkedInstruments"
        :available-instruments="availableInstruments"
        :can-edit="canEdit"
        @back="activeView = 'overview'"
        @add-instrument="addInstrument"
        @remove-instrument="removeInstrument"
      />
    </section>

    <el-dialog v-model="createDialogVisible" title="新建策略" width="520px">
      <div class="create-strategy-form">
        <el-input v-model="createForm.name" maxlength="120" show-word-limit placeholder="策略名称" />
        <el-select v-model="createForm.strategy_type" placeholder="策略类型">
          <el-option v-for="item in strategyTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="createForm.freq" placeholder="周期">
          <el-option v-for="item in strategyFreqOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-input v-model="createForm.strategy_idea" maxlength="8000" type="textarea" :rows="4" placeholder="策略思想：它试图捕捉什么市场现象" />
        <el-input v-model="createForm.description" maxlength="4000" type="textarea" :rows="4" placeholder="策略说明" />
      </div>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createStrategy">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, toRef, watch } from 'vue'
import StrategyEditor from './components/StrategyEditor.vue'
import StrategyInstrumentStudio from './components/StrategyInstrumentStudio.vue'
import StrategyList from './components/StrategyList.vue'
import StrategyVersionStudio from './components/StrategyVersionStudio.vue'
import { useStrategies } from './composables/useStrategies'
import {
  strategyFreqOptions,
  strategyStatusOptions,
  strategyTypeOptions,
  userManagedStrategyStatusOptions
} from './utils/labels'

const props = defineProps({
  token: {
    type: String,
    required: true
  },
  user: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['open-backtest'])
const activeView = ref('overview')
const selectedVersionId = ref(null)

const {
  loading,
  saving,
  selected,
  versions,
  linkedInstruments,
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
  useVersion
} = useStrategies(toRef(props, 'token'), toRef(props, 'user'))

const selectedVersion = computed(() => {
  if (!versions.value.length) return null
  return versions.value.find((item) => item.id === selectedVersionId.value) || versions.value[0]
})

const editableStatusOptions = computed(() => {
  if (props.user?.role === 'admin') return strategyStatusOptions
  const current = strategyStatusOptions.find((item) => item.value === selected.value?.status)
  if (!current || userManagedStrategyStatusOptions.some((item) => item.value === current.value)) {
    return userManagedStrategyStatusOptions
  }
  return [...userManagedStrategyStatusOptions, current]
})

watch(
  [versions, selected],
  ([versionList, currentStrategy]) => {
    if (!currentStrategy || !versionList.length) {
      selectedVersionId.value = null
      return
    }
    if (!selectedVersionId.value || !versionList.some((item) => item.id === selectedVersionId.value)) {
      selectedVersionId.value = versionList[0].id
    }
  },
  { immediate: true }
)

function openBacktestHistory() {
  emit('open-backtest', { strategy: selected.value, mode: 'history' })
}

function openQuickBacktest(strategy) {
  emit('open-backtest', { strategy, mode: 'quick' })
}

function openVersionStudio() {
  activeView.value = 'versions'
}

function openInstrumentStudio() {
  activeView.value = 'instruments'
}

function openCreateDialog() {
  activeView.value = 'overview'
  createDialogVisible.value = true
}

async function selectVersion(version) {
  if (!version) return
  const loaded = await loadVersion(version)
  if (loaded) selectedVersionId.value = loaded.id
}

async function handleSelectStrategy(item) {
  activeView.value = 'overview'
  await selectStrategy(item)
}
</script>

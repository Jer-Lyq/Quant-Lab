<template>
  <aside class="sidebar strategy-sidebar">
    <div class="sidebar-head">
      <h2>策略库</h2>
      <el-button class="sidebar-refresh" circle :disabled="loading" @click="$emit('refresh')">
        <RefreshCw :size="15" :class="{ 'is-refreshing': loading }" />
      </el-button>
    </div>
    <el-input :model-value="keyword" placeholder="搜索策略、说明或上传者" @update:model-value="$emit('update:keyword', $event)">
      <template #prefix><Search :size="16" /></template>
    </el-input>
    <div class="strategy-filters">
      <el-select :model-value="typeFilter" placeholder="类型" clearable @update:model-value="$emit('update:typeFilter', $event)">
        <el-option v-for="item in strategyTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select :model-value="statusFilter" placeholder="状态" clearable @update:model-value="$emit('update:statusFilter', $event)">
        <el-option v-for="item in strategyStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
    </div>
    <el-button class="wide-button strategy-create-button" type="primary" @click="$emit('create')">
      <Plus :size="16" />
      新建策略
    </el-button>
    <div class="instrument-list">
      <div
        v-for="item in strategies"
        :key="item.id"
        class="instrument-row strategy-row"
        :class="{ active: selected?.id === item.id }"
      >
        <button class="instrument-item" @click="$emit('select', item)">
          <span>
            <strong>{{ item.name }}</strong>
            <small>{{ strategyTypeLabel(item.strategy_type) }} · {{ strategyStatusLabel(item.status) }}</small>
            <small>{{ item.latest_version_name || '暂无代码版本' }} · {{ item.instrument_count || 0 }} 个标的</small>
          </span>
          <em>{{ strategyFreqLabel(item.freq) }}</em>
        </button>
        <button
          v-if="canDelete(item)"
          class="instrument-delete"
          type="button"
          :aria-label="`删除 ${item.name}`"
          :title="`删除 ${item.name}`"
          :disabled="loading"
          @click="$emit('delete', item)"
        >
          <Trash2 :size="14" />
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { Plus, RefreshCw, Search, Trash2 } from '@lucide/vue'
import {
  strategyFreqLabel,
  strategyStatusLabel,
  strategyStatusOptions,
  strategyTypeLabel,
  strategyTypeOptions
} from '../utils/labels'

const props = defineProps({
  strategies: {
    type: Array,
    default: () => []
  },
  selected: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  keyword: {
    type: String,
    default: ''
  },
  statusFilter: {
    type: String,
    default: ''
  },
  typeFilter: {
    type: String,
    default: ''
  },
  user: {
    type: Object,
    default: null
  }
})

defineEmits([
  'update:keyword',
  'update:statusFilter',
  'update:typeFilter',
  'refresh',
  'create',
  'select',
  'delete'
])

function canDelete(item) {
  return props.user?.role === 'admin' || item.author_id === props.user?.id
}
</script>

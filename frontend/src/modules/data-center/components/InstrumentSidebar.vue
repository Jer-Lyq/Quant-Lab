<template>
  <aside class="sidebar">
    <div class="sidebar-head">
      <h2>研究标的</h2>
      <el-button class="sidebar-refresh" circle :disabled="loading" @click="$emit('refresh')">
        <RefreshCw :size="15" :class="{ 'is-refreshing': loading }" />
      </el-button>
    </div>
    <el-input :model-value="keyword" placeholder="搜索代码或名称" @update:model-value="$emit('update:keyword', $event)">
      <template #prefix><Search :size="16" /></template>
    </el-input>
    <div class="instrument-list">
      <div
        v-for="item in instruments"
        :key="item.id"
        class="instrument-row"
        :class="{ active: selected?.id === item.id }"
      >
        <button class="instrument-item" @click="$emit('select', item)">
          <span>
            <strong>{{ item.name }}</strong>
            <small>{{ item.ts_code }} · {{ typeLabel(item.asset_type) }}</small>
          </span>
          <em>{{ item.status }}</em>
        </button>
        <button
          v-if="isAdmin"
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
import { RefreshCw, Search, Trash2 } from '@lucide/vue'
import { typeLabel } from '../utils/labels'

defineProps({
  keyword: {
    type: String,
    default: ''
  },
  instruments: {
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
  isAdmin: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:keyword', 'refresh', 'select', 'delete'])
</script>

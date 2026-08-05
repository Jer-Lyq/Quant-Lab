<template>
  <div class="detail-head">
    <div>
      <p class="product-mark">{{ instrument.ts_code }}</p>
      <h2>{{ instrument.name }}</h2>
      <p class="subtle">
        {{ typeLabel(instrument.asset_type) }} · {{ instrument.market || '市场未知' }} · 最近同步 {{ instrument.last_synced_at || '暂无' }}
      </p>
    </div>
    <div class="detail-actions">
      <el-segmented :model-value="freq" :options="freqOptions" @change="changeFreq" />
      <el-button v-if="isAdmin" :loading="loading" @click="$emit('sync')">
        <RefreshCw :size="16" />
        同步
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { RefreshCw } from '@lucide/vue'
import { freqOptions, typeLabel } from '../utils/labels'

defineProps({
  instrument: {
    type: Object,
    required: true
  },
  freq: {
    type: String,
    required: true
  },
  isAdmin: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:freq', 'load-bars', 'sync'])

function changeFreq(value) {
  emit('update:freq', value)
  emit('load-bars')
}
</script>

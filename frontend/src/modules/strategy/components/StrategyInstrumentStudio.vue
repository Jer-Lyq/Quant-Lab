<template>
  <section class="strategy-instrument-studio">
    <div class="strategy-version-studio-header">
      <div>
        <p class="product-mark">关联标的</p>
        <h2>{{ strategy?.name || '关联标的' }}</h2>
      </div>
      <div class="strategy-version-studio-actions">
        <el-button @click="$emit('back')">返回策略</el-button>
      </div>
    </div>

    <section class="strategy-instrument-studio-panel">
      <StrategyInstrumentPanel
        :linked-instruments="linkedInstruments"
        :available-instruments="availableInstruments"
        :can-edit="canEdit"
        studio
        @add="$emit('add-instrument', $event)"
        @remove="$emit('remove-instrument', $event)"
      />
    </section>
  </section>
</template>

<script setup>
import StrategyInstrumentPanel from './StrategyInstrumentPanel.vue'

defineProps({
  strategy: {
    type: Object,
    default: null
  },
  linkedInstruments: {
    type: Array,
    default: () => []
  },
  availableInstruments: {
    type: Array,
    default: () => []
  },
  canEdit: {
    type: Boolean,
    default: false
  }
})

defineEmits(['back', 'add-instrument', 'remove-instrument'])
</script>

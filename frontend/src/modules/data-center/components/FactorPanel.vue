<template>
  <aside class="factor-panel">
    <div class="panel-title-row">
      <div>
        <h3>策略因子</h3>
        <p class="subtle">仅展示当前计算值和历史分位，不给出结论。</p>
      </div>
    </div>
    <div class="factor-groups">
      <section v-for="group in groups" :key="group.name" class="factor-group">
        <h4>{{ group.name }}</h4>
        <div class="factor-list">
          <div v-for="factor in group.items" :key="factor.key" class="factor-row">
            <div>
              <span>{{ factor.label }}</span>
              <strong>{{ factorValue(factor) }}</strong>
            </div>
            <div class="percentile">
              <i :style="{ width: percentileWidth(factor.percentile) }"></i>
              <em>{{ percentileText(factor.percentile) }}</em>
            </div>
          </div>
        </div>
      </section>
    </div>
  </aside>
</template>

<script setup>
import { factorValue, percentileText, percentileWidth } from '../utils/formatters'

defineProps({
  groups: {
    type: Array,
    default: () => []
  }
})
</script>

<template>
  <section class="content backtest-content">
    <section class="admin-panel backtest-handoff-panel">
      <div class="backtest-handoff-header">
        <div>
          <h2>{{ target?.mode === 'history' ? '回测记录' : '启动回测' }}</h2>
          <p class="subtle">
            {{ target?.strategy
              ? `已从策略库带入「${target.strategy.name}」。这里将直接创建回测任务。`
              : '从策略库选择策略后，可以在这里启动回测或查看记录。' }}
          </p>
        </div>
        <el-button @click="$emit('back-to-strategy')">
          <ArrowLeft :size="16" />
          返回策略库
        </el-button>
      </div>

      <div class="backtest-handoff-grid">
        <div class="handoff-summary">
          <span class="field-label">当前策略</span>
          <strong>{{ target?.strategy?.name || '尚未选择策略' }}</strong>
          <small>{{ strategyContextText }}</small>
        </div>
        <div class="handoff-summary">
          <span class="field-label">入口模式</span>
          <strong>{{ target?.mode === 'history' ? '查看回测记录' : '创建回测任务' }}</strong>
          <small>此入口已经保留策略上下文，后续不需要再次选择。</small>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowLeft } from '@lucide/vue'

const props = defineProps({
  target: {
    type: Object,
    default: null
  }
})

const strategyContextText = computed(() => {
  if (!props.target?.strategy) return '请从策略库进入，以带入需要研究的策略。'
  return props.target.strategy.strategy_idea || '该策略暂未填写策略思想。'
})

defineEmits(['back-to-strategy'])
</script>

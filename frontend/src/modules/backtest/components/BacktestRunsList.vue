<template>
  <aside class="backtest-runs-rail">
    <div class="backtest-runs-head">
      <div>
        <h2>回测记录</h2>
        <p>{{ runs.length }} 个任务</p>
      </div>
      <el-button class="icon-action-button backtest-refresh" title="刷新回测记录" :loading="loading" @click="$emit('refresh')">
        <RefreshCw :size="16" />
      </el-button>
    </div>

    <div v-if="runs.length" class="backtest-run-list">
      <button
        v-for="run in runs"
        :key="run.id"
        class="backtest-run-row"
        :class="{ active: selected?.id === run.id }"
        type="button"
        @click="$emit('select', run)"
      >
        <span class="backtest-run-row-head">
          <strong>#{{ run.id }} · {{ run.instrument_name || run.ts_code || '标的已移除' }}</strong>
          <span class="backtest-status-chip" :class="`status-${run.status}`">{{ backtestStatusLabels[run.status] || run.status }}</span>
        </span>
        <span>{{ run.version_name }} · {{ run.start_date }} 至 {{ run.end_date }}</span>
        <small>{{ formatDateTime(run.created_at) }}</small>
      </button>
    </div>

    <div v-else class="backtest-run-empty">
      <FlaskConical :size="22" />
      <span>暂无回测记录</span>
    </div>
  </aside>
</template>

<script setup>
import { FlaskConical, RefreshCw } from '@lucide/vue'
import { backtestStatusLabels, formatDateTime } from '../utils/labels'

defineProps({
  runs: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
  loading: { type: Boolean, default: false }
})

defineEmits(['refresh', 'select'])
</script>

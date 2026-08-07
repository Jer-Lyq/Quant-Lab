<template>
  <div class="backtest-layout">
    <BacktestRunsList
      :runs="runs"
      :selected="selectedRun"
      :loading="loading"
      @refresh="loadRuns"
      @select="selectRun"
    />

    <section class="content backtest-content">
      <BacktestForm
        :strategy="strategy"
        :options="options"
        :form="form"
        :submitting="submitting"
        :can-create="canCreate"
        @create="createRun"
        @back-to-strategy="$emit('back-to-strategy')"
      />

      <section v-if="selectedRun" class="backtest-result-shell">
        <div class="backtest-status-band">
          <div class="backtest-status-identity">
            <span class="backtest-status-icon" :class="`status-${selectedRun.status}`">
              <LoaderCircle v-if="activeBacktestStatuses.has(selectedRun.status)" :size="18" />
              <CircleCheck v-else-if="selectedRun.status === 'success'" :size="18" />
              <CircleX v-else :size="18" />
            </span>
            <div>
              <h2>#{{ selectedRun.id }} · {{ selectedRun.instrument_name || selectedRun.ts_code }}</h2>
              <p>{{ selectedRun.version_name }} · {{ selectedRun.start_date }} 至 {{ selectedRun.end_date }}</p>
            </div>
          </div>
          <div class="backtest-status-actions">
            <span class="backtest-status-chip" :class="`status-${selectedRun.status}`">
              {{ backtestStatusLabels[selectedRun.status] || selectedRun.status }}
            </span>
            <el-button
              v-if="activeBacktestStatuses.has(selectedRun.status)"
              class="backtest-cancel-button"
              @click="cancelRun(selectedRun)"
            >
              <Square :size="14" />
              取消
            </el-button>
          </div>
        </div>

        <div v-if="selectedRun.result_warning" class="backtest-warning">
          <TriangleAlert :size="17" />
          <span>{{ selectedRun.result_warning }}</span>
        </div>

        <div v-if="selectedRun.status === 'failed'" class="backtest-error">
          <CircleX :size="18" />
          <div>
            <strong>回测未完成</strong>
            <p>{{ selectedRun.error_message || '执行器返回失败，请检查任务日志。' }}</p>
          </div>
        </div>

        <div v-else-if="activeBacktestStatuses.has(selectedRun.status)" class="backtest-running-state">
          <LoaderCircle :size="24" />
          <div>
            <strong>{{ selectedRun.status === 'running' ? '执行器正在运行' : '等待 Worker 领取任务' }}</strong>
            <p>页面会自动刷新任务状态。</p>
          </div>
        </div>

        <template v-else-if="selectedRun.status === 'success'">
          <BacktestResultCards :summary="artifacts.summary || selectedRun" />
          <BacktestCurveChart
            :equity="artifacts.equity_curve || []"
            :drawdown="artifacts.drawdown_curve || []"
          />
          <BacktestTradesTable :trades="artifacts.trades || []" />
        </template>
      </section>

      <section v-else class="backtest-result-empty">
        <FlaskConical :size="26" />
        <h2>选择一条回测记录</h2>
        <p>任务状态和结果将在这里展示。</p>
      </section>
    </section>
  </div>
</template>

<script setup>
import { toRef } from 'vue'
import { CircleCheck, CircleX, FlaskConical, LoaderCircle, Square, TriangleAlert } from '@lucide/vue'
import BacktestCurveChart from './components/BacktestCurveChart.vue'
import BacktestForm from './components/BacktestForm.vue'
import BacktestResultCards from './components/BacktestResultCards.vue'
import BacktestRunsList from './components/BacktestRunsList.vue'
import BacktestTradesTable from './components/BacktestTradesTable.vue'
import { useBacktests } from './composables/useBacktests'
import { activeBacktestStatuses, backtestStatusLabels } from './utils/labels'

const props = defineProps({
  token: { type: String, required: true },
  target: { type: Object, default: null }
})

defineEmits(['back-to-strategy'])

const {
  loading,
  submitting,
  options,
  runs,
  selectedRun,
  artifacts,
  form,
  strategy,
  canCreate,
  loadRuns,
  selectRun,
  createRun,
  cancelRun
} = useBacktests(toRef(props, 'token'), toRef(props, 'target'))
</script>

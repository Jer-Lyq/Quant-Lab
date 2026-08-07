<template>
  <section class="backtest-launch-panel">
    <div class="backtest-section-head">
      <div>
        <h2>{{ strategy?.name || '创建回测任务' }}</h2>
        <p class="subtle">{{ strategy ? '选择不可变代码版本、标的和研究区间。' : '请先从策略库选择一个策略。' }}</p>
      </div>
      <el-button @click="$emit('back-to-strategy')">
        <ArrowLeft :size="16" />
        返回策略库
      </el-button>
    </div>

    <div v-if="strategy" class="backtest-form-grid">
      <label class="field-block">
        <span class="field-label">代码版本</span>
        <el-select v-model="form.strategy_version_id" placeholder="选择校验通过的版本">
          <el-option
            v-for="version in options.versions"
            :key="version.id"
            :label="version.validation_status === 'valid' ? version.version_name : `${version.version_name} · 校验未通过`"
            :value="version.id"
            :disabled="version.validation_status !== 'valid'"
          />
        </el-select>
      </label>

      <label class="field-block">
        <span class="field-label">交易标的</span>
        <el-select v-model="form.instrument_id" placeholder="选择关联标的">
          <el-option
            v-for="instrument in options.instruments"
            :key="instrument.id"
            :label="`${instrument.name} · ${instrument.ts_code}`"
            :value="instrument.id"
            :disabled="!instrument.backtest_supported || instrument.bar_count < 2"
          />
        </el-select>
      </label>

      <label class="field-block backtest-date-field">
        <span class="field-label">回测区间</span>
        <el-date-picker
          v-model="form.date_range"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          unlink-panels
        />
      </label>

      <label class="field-block">
        <span class="field-label">初始资金</span>
        <el-input-number v-model="form.initial_cash" :min="10000" :max="10000000000" :step="100000" controls-position="right" />
      </label>

      <label class="field-block">
        <span class="field-label">价格口径</span>
        <el-select v-model="form.adjustment_mode">
          <el-option label="前复权" value="qfq" />
          <el-option label="原始价格" value="raw" />
        </el-select>
      </label>

      <label class="field-block">
        <span class="field-label">佣金率</span>
        <el-input-number v-model="form.commission_rate" :min="0" :max="0.02" :step="0.0001" :precision="4" controls-position="right" />
      </label>

      <label class="field-block">
        <span class="field-label">滑点率</span>
        <el-input-number v-model="form.slippage_rate" :min="0" :max="0.02" :step="0.0001" :precision="4" controls-position="right" />
      </label>

      <label class="field-block">
        <span class="field-label">基准代码</span>
        <el-input v-model="form.benchmark" maxlength="40" placeholder="可选，如 000300.XSHG" />
      </label>

      <el-button class="backtest-run-button" type="primary" :loading="submitting" :disabled="!canCreate" @click="$emit('create')">
        <Play :size="16" />
        启动回测
      </el-button>
    </div>

    <div v-else class="backtest-no-strategy">
      <LibraryBig :size="24" />
      <strong>尚未选择策略</strong>
      <el-button type="primary" @click="$emit('back-to-strategy')">进入策略库</el-button>
    </div>
  </section>
</template>

<script setup>
import { ArrowLeft, LibraryBig, Play } from '@lucide/vue'

defineProps({
  strategy: { type: Object, default: null },
  options: { type: Object, default: () => ({ versions: [], instruments: [] }) },
  form: { type: Object, required: true },
  submitting: { type: Boolean, default: false },
  canCreate: { type: Boolean, default: false }
})

defineEmits(['create', 'back-to-strategy'])
</script>

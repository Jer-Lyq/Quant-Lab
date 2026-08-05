<template>
  <section class="admin-panel">
    <div class="panel-title-row">
      <div>
        <h2>管理员录入</h2>
        <p class="subtle">录入标的后同步行情，前台只展示已发布的数据。</p>
      </div>
    </div>
    <div class="admin-grid">
      <el-input v-model="newInstrument.ts_code" placeholder="例如 000001.SZ / 000300.SH" />
      <el-select v-model="newInstrument.asset_type">
        <el-option label="股票" value="stock" />
        <el-option label="ETF" value="etf" />
        <el-option label="指数" value="index" />
        <el-option label="基金" value="fund" />
      </el-select>
      <el-date-picker v-model="newInstrument.data_start" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" />
      <el-date-picker v-model="newInstrument.data_end" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" />
      <el-button class="admin-action-button" type="primary" :loading="loading" @click="$emit('create-and-sync')">
        <Plus :size="16" />
        新增并同步
      </el-button>
    </div>
  </section>
</template>

<script setup>
import { Plus } from '@lucide/vue'

defineProps({
  newInstrument: {
    type: Object,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['create-and-sync'])
</script>

<template>
  <section class="backtest-trades-panel">
    <div class="backtest-section-head compact">
      <div>
        <h3>成交明细</h3>
        <p class="subtle">共 {{ trades.length }} 条成交。</p>
      </div>
    </div>
    <el-table :data="trades" empty-text="暂无成交" height="360">
      <el-table-column prop="datetime" label="时间" min-width="160" />
      <el-table-column prop="order_book_id" label="标的" min-width="130" />
      <el-table-column prop="side" label="方向" width="90" />
      <el-table-column prop="last_price" label="成交价" min-width="110">
        <template #default="scope">{{ formatNumber(scope.row.last_price, 4) }}</template>
      </el-table-column>
      <el-table-column prop="quantity" label="数量" min-width="100">
        <template #default="scope">{{ formatNumber(scope.row.quantity, 0) }}</template>
      </el-table-column>
      <el-table-column prop="transaction_cost" label="费用" min-width="110">
        <template #default="scope">{{ formatNumber(scope.row.transaction_cost, 2) }}</template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { formatNumber } from '../utils/labels'

defineProps({ trades: { type: Array, default: () => [] } })
</script>

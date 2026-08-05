<template>
  <section class="table-wrap">
    <div class="panel-title-row table-title">
      <div>
        <h3>最近行情</h3>
        <p class="subtle">按交易日期倒序展示最近 80 条。</p>
      </div>
    </div>
    <el-table :data="bars" height="340">
      <el-table-column prop="trade_date" label="日期" width="120" />
      <el-table-column prop="open" label="开盘" />
      <el-table-column prop="high" label="最高" />
      <el-table-column prop="low" label="最低" />
      <el-table-column prop="close" label="收盘" />
      <el-table-column prop="volume" label="成交量" />
      <el-table-column prop="amount" label="成交额" />
    </el-table>
  </section>
</template>

<script setup>
defineProps({
  bars: {
    type: Array,
    default: () => []
  }
})
</script>

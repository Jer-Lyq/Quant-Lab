<template>
  <div class="empty-state">
    <Database :size="42" />
    <h2>选择一个标的开始研究</h2>
    <p>当前页面只展示管理员录入并发布的行情、指标和因子数据。</p>
  </div>
</template>

<script setup>
import { Database } from '@lucide/vue'
</script>

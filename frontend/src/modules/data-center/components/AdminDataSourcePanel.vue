<template>
  <section class="admin-panel data-source-panel">
    <div class="panel-title-row">
      <div>
        <h2>数据源接口</h2>
        <p class="subtle">当前先接入 Tushare，工程结构为后续数据源保留 provider 扩展口。</p>
        <p class="subtle">当前接口：{{ dataSource.connection.http_url || dataSourceForm.tushare_http_url }}</p>
      </div>
      <span class="source-status" :class="{ ready: dataSource.connection.configured }">
        {{ dataSource.connection.configured ? '已配置' : '未配置' }}
        <template v-if="dataSource.connection.token_masked"> · {{ dataSource.connection.token_masked }}</template>
      </span>
    </div>
    <div class="data-source-grid">
      <input
        v-model="dataSourceForm.tushare_token"
        class="source-input"
        type="text"
        placeholder="粘贴新的 Tushare Token"
        autocomplete="off"
        spellcheck="false"
      />
      <input
        v-model="dataSourceForm.tushare_http_url"
        class="source-input"
        type="url"
        placeholder="https://tuaremax.top"
        autocomplete="off"
        spellcheck="false"
      />
      <el-button :loading="loading" @click="$emit('save')">
        <KeyRound :size="16" />
        保存接口
      </el-button>
      <el-button type="primary" :disabled="!selected" :loading="loading" @click="$emit('save-and-sync')">
        <RefreshCw :size="16" />
        保存并同步当前标的
      </el-button>
    </div>
  </section>
</template>

<script setup>
import { KeyRound, RefreshCw } from '@lucide/vue'

defineProps({
  dataSource: {
    type: Object,
    required: true
  },
  dataSourceForm: {
    type: Object,
    required: true
  },
  selected: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['save', 'save-and-sync'])
</script>

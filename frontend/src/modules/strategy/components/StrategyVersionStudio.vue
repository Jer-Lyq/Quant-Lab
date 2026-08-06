<template>
  <section class="strategy-version-studio">
    <div class="strategy-version-studio-header">
      <div>
        <p class="product-mark">代码版本</p>
        <h2>{{ strategy?.name || '代码版本' }}</h2>
        <p class="subtle">每个版本都是不可变快照。选中一条，就能直接看到对应代码。</p>
      </div>
      <div class="strategy-version-studio-actions">
        <el-button @click="$emit('back')">返回策略</el-button>
        <el-button type="primary" :disabled="!canEdit" :loading="saving" @click="$emit('save-version')">
          保存版本
        </el-button>
      </div>
    </div>

    <div class="strategy-version-studio-grid">
      <StrategyVersionPanel
        :versions="versions"
        :selected-version="selectedVersion"
        :can-edit="canEdit"
        @select-version="$emit('select-version', $event)"
        @use-version="$emit('use-version', $event)"
        @delete-version="$emit('delete-version', $event)"
      />

      <section class="strategy-version-detail">
        <div v-if="selectedVersion" class="strategy-version-detail-shell">
          <div class="strategy-version-detail-head">
            <div>
              <h3>{{ selectedVersion.version_name }}</h3>
              <p class="subtle">
                {{ selectedVersion.created_at }} · {{ selectedVersion.created_by_name || '未知' }}
              </p>
            </div>
            <el-tag :type="selectedVersion.validation_status === 'valid' ? 'success' : 'warning'" effect="plain">
              {{ selectedVersion.validation_status === 'valid' ? '结构通过' : selectedVersion.validation_message || '待校验' }}
            </el-tag>
          </div>

          <div class="version-detail-meta">
            <div>
              <span class="field-label">说明</span>
              <p>{{ selectedVersion.notes || '这条版本还没有填写说明。' }}</p>
            </div>
            <div>
              <span class="field-label">哈希</span>
              <p>{{ selectedVersion.code_hash }}</p>
            </div>
          </div>

          <div class="strategy-version-detail-actions">
            <el-button :disabled="!canEdit" @click="$emit('use-version', selectedVersion)">载入到编辑器</el-button>
            <el-button
              :disabled="!canEdit"
              type="danger"
              plain
              @click="$emit('delete-version', selectedVersion)"
            >
              删除版本
            </el-button>
          </div>

          <textarea class="code-editor code-viewer" :value="selectedVersion.code" readonly spellcheck="false" />
        </div>

        <div v-else class="empty-state strategy-version-empty">
          <h3>还没有代码版本</h3>
          <p>先在策略页保存一次版本，再回来这里查看具体代码快照。</p>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import StrategyVersionPanel from './StrategyVersionPanel.vue'

defineProps({
  strategy: {
    type: Object,
    default: null
  },
  versions: {
    type: Array,
    default: () => []
  },
  selectedVersion: {
    type: Object,
    default: null
  },
  canEdit: {
    type: Boolean,
    default: false
  },
  saving: {
    type: Boolean,
    default: false
  }
})

defineEmits(['back', 'save-version', 'select-version', 'use-version', 'delete-version'])
</script>

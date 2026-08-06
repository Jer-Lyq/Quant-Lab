<template>
  <section class="strategy-property-block">
    <div class="property-block-head">
      <div>
        <span class="field-label">代码版本</span>
        <p class="subtle">不可变快照，载入后可另存为新版本。</p>
      </div>
      <el-tag size="small" effect="plain">{{ versions.length }}</el-tag>
    </div>
    <div v-if="versions.length" class="version-list">
      <div
        v-for="version in versions"
        :key="version.id"
        class="version-row"
        :class="{ active: selectedVersion?.id === version.id }"
        role="button"
        tabindex="0"
        @click="$emit('select-version', version)"
        @keydown.enter.prevent="$emit('select-version', version)"
        @keydown.space.prevent="$emit('select-version', version)"
      >
        <div>
          <strong>{{ version.version_name }}</strong>
          <small>{{ version.created_at }} · {{ version.created_by_name || '未知' }}</small>
          <small :class="['validation-chip', version.validation_status]">
            {{ version.validation_status === 'valid' ? '结构通过' : version.validation_message }}
          </small>
        </div>
        <div class="version-actions">
          <el-button size="small" :disabled="!canEdit" @click="$emit('use-version', version)">载入</el-button>
          <el-button
            class="version-delete-button"
            size="small"
            text
            :disabled="!canEdit"
            :aria-label="`删除版本 ${version.version_name}`"
            :title="`删除版本 ${version.version_name}`"
            @click.stop="$emit('delete-version', version)"
          >
            <Trash2 :size="14" />
          </el-button>
        </div>
      </div>
    </div>
    <p v-else class="subtle property-empty">还没有保存过代码版本。</p>
  </section>
</template>

<script setup>
import { Trash2 } from '@lucide/vue'

defineProps({
  versions: { type: Array, default: () => [] },
  selectedVersion: { type: Object, default: null },
  canEdit: { type: Boolean, default: false }
})

defineEmits(['select-version', 'use-version', 'delete-version'])
</script>

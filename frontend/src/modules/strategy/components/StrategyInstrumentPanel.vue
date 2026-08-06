<template>
  <section class="strategy-property-block" :class="{ 'instrument-studio-block': studio }">
    <div class="property-block-head">
      <div>
        <span class="field-label">关联标的</span>
      </div>
      <el-tag size="small" effect="plain">{{ linkedInstruments.length }}</el-tag>
    </div>
    <div class="instrument-linker">
      <el-select
        v-model="instrumentToAdd"
        :disabled="!canEdit || !availableInstruments.length"
        filterable
        placeholder="选择数据中心标的"
      >
        <el-option
          v-for="item in availableInstruments"
          :key="item.id"
          :label="`${item.name} ${item.ts_code}`"
          :value="item.id"
        />
      </el-select>
      <el-button :disabled="!canEdit || !instrumentToAdd" @click="addSelected">关联</el-button>
    </div>
    <div v-if="linkedInstruments.length" class="linked-list">
      <div v-for="item in linkedInstruments" :key="item.id" class="linked-row">
        <span>
          <strong>{{ item.name }}</strong>
          <small>{{ item.ts_code }} · {{ item.asset_type }}</small>
        </span>
        <el-button size="small" text :disabled="!canEdit" @click="$emit('remove', item.id)">移除</el-button>
      </div>
    </div>
    <p v-else class="subtle property-empty">暂未关联标的。</p>
  </section>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  linkedInstruments: { type: Array, default: () => [] },
  availableInstruments: { type: Array, default: () => [] },
  canEdit: { type: Boolean, default: false },
  studio: { type: Boolean, default: false }
})

const emit = defineEmits(['add', 'remove'])
const instrumentToAdd = ref(null)

function addSelected() {
  emit('add', instrumentToAdd.value)
  instrumentToAdd.value = null
}
</script>

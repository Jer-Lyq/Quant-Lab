<template>
  <section class="strategy-editor">
    <div v-if="strategy" class="strategy-editor-stack">
      <section class="admin-panel strategy-properties-panel">
        <div class="strategy-property-header">
          <div class="strategy-identity">
            <p class="product-mark">{{ strategy.author_name || '上传者未知' }}</p>
            <div class="strategy-title-line">
              <h2>{{ strategy.name }}</h2>
              <el-tag size="small" effect="plain">{{ strategyStatusLabel(editorForm.status) }}</el-tag>
            </div>
          </div>
          <div class="strategy-property-actions">
            <el-button class="quick-backtest-action" @click="$emit('quick-backtest', strategy)">
              <FlaskConical :size="16" />
              快速回测
            </el-button>
            <el-tooltip content="历史回测" placement="bottom">
              <el-button
                class="secondary-action icon-action-button"
                aria-label="历史回测"
                title="历史回测"
                @click="$emit('open-history')"
              >
                <History :size="16" />
              </el-button>
            </el-tooltip>
            <el-tooltip content="保存属性" placement="bottom">
              <el-button
                type="primary"
                class="icon-action-button"
                :disabled="!canEdit"
                :loading="saving"
                aria-label="保存属性"
                title="保存属性"
                @click="$emit('save-strategy')"
              >
                <Save :size="16" />
              </el-button>
            </el-tooltip>
          </div>
        </div>

        <div class="strategy-form-grid">
          <div class="field-block">
            <span class="field-label">策略名称</span>
            <el-input v-model="editorForm.name" :disabled="!canEdit" placeholder="例如：双均线趋势策略" />
          </div>
          <div class="field-block">
            <span class="field-label">策略类型</span>
            <el-select v-model="editorForm.strategy_type" :disabled="!canEdit" placeholder="选择类型">
              <el-option v-for="item in strategyTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </div>
          <div class="field-block">
            <span class="field-label">状态</span>
            <el-select v-model="editorForm.status" :disabled="!canEdit" placeholder="选择状态">
              <el-option v-for="item in strategyStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </div>
          <div class="field-block">
            <span class="field-label">频率</span>
            <el-select v-model="editorForm.freq" :disabled="!canEdit" placeholder="选择频率">
              <el-option v-for="item in strategyFreqOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </div>
          <div class="field-block">
            <span class="field-label">市场</span>
            <el-input v-model="editorForm.market" :disabled="!canEdit" placeholder="例如：A股 / ETF" />
          </div>
        </div>

        <div class="strategy-text-grid">
          <div class="field-block">
            <span class="field-label">策略思想</span>
            <el-input
              v-model="editorForm.strategy_idea"
              :disabled="!canEdit"
              type="textarea"
              :rows="5"
              placeholder="说明你为什么设计这个策略，它试图捕捉什么市场现象。"
            />
          </div>
          <div class="field-block">
            <span class="field-label">策略说明</span>
            <el-input
              v-model="editorForm.description"
              :disabled="!canEdit"
              type="textarea"
              :rows="5"
              placeholder="记录策略来源、核心逻辑和适用环境。"
            />
          </div>
          <div class="field-block">
            <span class="field-label">上传者备注</span>
            <el-input
              v-model="editorForm.uploader_notes"
              :disabled="!canEdit"
              type="textarea"
              :rows="5"
              placeholder="记录改动、风险提示和待验证问题。"
            />
          </div>
        </div>
      </section>

      <section class="admin-panel code-panel">
        <div class="code-panel-header">
          <div>
            <h3>RQAlpha 策略代码</h3>
          </div>
          <div class="code-panel-actions">
            <el-button class="secondary-action" @click="$emit('open-versions')">
              <History :size="16" />
              代码版本
            </el-button>
            <el-button class="secondary-action" @click="$emit('open-instruments')">
              <Database :size="16" />
              关联标的
            </el-button>
            <el-button type="primary" :disabled="!canEdit" :loading="saving" @click="$emit('save-version')">
              <GitCommitHorizontal :size="16" />
              保存版本
            </el-button>
          </div>
        </div>
        <div class="version-meta-grid">
          <div class="field-block compact-field">
            <span class="field-label">版本名称</span>
            <el-input v-model="versionForm.version_name" :disabled="!canEdit" placeholder="留空自动生成" />
          </div>
          <div class="field-block compact-field">
            <span class="field-label">版本说明</span>
            <el-input v-model="versionForm.notes" :disabled="!canEdit" placeholder="记录这次修改的重点" />
          </div>
        </div>
        <textarea
          v-model="versionForm.code"
          class="code-editor"
          :disabled="!canEdit"
          spellcheck="false"
          aria-label="RQAlpha 策略代码"
        />
      </section>
    </div>

    <div v-else class="empty-state strategy-empty">
      <h2>还没有策略</h2>
      <p>新建一个 RQAlpha 风格策略，先把代码和研究思想沉淀下来。</p>
    </div>
  </section>
</template>

<script setup>
import { Database, FlaskConical, GitCommitHorizontal, History, Save } from '@lucide/vue'
import {
  strategyFreqOptions,
  strategyStatusLabel,
  strategyStatusOptions,
  strategyTypeOptions
} from '../utils/labels'

defineProps({
  strategy: { type: Object, default: null },
  editorForm: { type: Object, required: true },
  versionForm: { type: Object, required: true },
  versions: { type: Array, default: () => [] },
  canEdit: { type: Boolean, default: false },
  saving: { type: Boolean, default: false }
})

defineEmits([
  'save-strategy',
  'save-version',
  'quick-backtest',
  'open-history',
  'open-versions',
  'open-instruments'
])
</script>

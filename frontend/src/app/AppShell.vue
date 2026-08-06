<template>
  <section class="workspace">
    <header class="topbar">
      <div>
        <p class="product-mark">Quant Lab</p>
        <h1>{{ title }}</h1>
      </div>
      <div class="topbar-actions">
        <nav v-if="modules.length" class="module-nav" aria-label="主模块">
          <button
            v-for="module in modules"
            :key="module.value"
            class="module-nav-item"
            :class="{ active: activeModule === module.value }"
            type="button"
            :aria-pressed="activeModule === module.value"
            @click="$emit('update:activeModule', module.value)"
          >
            <Database v-if="module.value === 'data-center'" :size="15" />
            <LibraryBig v-else-if="module.value === 'strategy'" :size="15" />
            <FlaskConical v-else :size="15" />
            <span>{{ module.label }}</span>
          </button>
        </nav>
        <span class="user-pill">{{ user?.username }} · {{ roleLabel }}</span>
        <el-button class="logout-button" @click="$emit('logout')">
          <LogOut :size="15" />
          退出
        </el-button>
      </div>
    </header>

    <slot />
  </section>
</template>

<script setup>
import { Database, FlaskConical, LibraryBig, LogOut } from '@lucide/vue'

defineProps({
  title: {
    type: String,
    required: true
  },
  user: {
    type: Object,
    default: null
  },
  roleLabel: {
    type: String,
    required: true
  },
  modules: {
    type: Array,
    default: () => []
  },
  activeModule: {
    type: String,
    default: ''
  }
})

defineEmits(['logout', 'update:activeModule'])
</script>

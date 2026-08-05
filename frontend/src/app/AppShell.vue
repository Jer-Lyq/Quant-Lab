<template>
  <section class="workspace">
    <header class="topbar">
      <div>
        <p class="product-mark">Quant Lab</p>
        <h1>{{ title }}</h1>
      </div>
      <div class="topbar-actions">
        <span class="user-pill">{{ user?.username }} · {{ roleLabel }}</span>
        <el-button @click="$emit('logout')">退出</el-button>
      </div>
    </header>

    <slot />
  </section>
</template>

<script setup>
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
  }
})

defineEmits(['logout'])
</script>

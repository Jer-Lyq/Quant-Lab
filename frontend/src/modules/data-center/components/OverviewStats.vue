<template>
  <div class="overview-grid">
    <div v-for="card in cards" :key="card.key" class="stat-box">
      <span>{{ card.label }}</span>
      <strong>{{ card.value }}</strong>
      <small>{{ card.meta }}</small>
    </div>
  </div>
</template>

<script setup>
defineProps({
  cards: {
    type: Array,
    default: () => []
  }
})
</script>

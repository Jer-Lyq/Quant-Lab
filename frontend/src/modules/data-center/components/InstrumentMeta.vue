<template>
  <section class="meta-panel">
    <h3>标的信息</h3>
    <dl>
      <div>
        <dt>行业</dt>
        <dd>{{ instrument.industry || '-' }}</dd>
      </div>
      <div>
        <dt>地区</dt>
        <dd>{{ instrument.area || '-' }}</dd>
      </div>
      <div>
        <dt>数据条数</dt>
        <dd>{{ barCount }}</dd>
      </div>
      <div>
        <dt>处理模块</dt>
        <dd>Market Engine</dd>
      </div>
    </dl>
  </section>
</template>

<script setup>
defineProps({
  instrument: {
    type: Object,
    required: true
  },
  barCount: {
    type: Number,
    default: 0
  }
})
</script>

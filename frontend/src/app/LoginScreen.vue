<template>
  <section class="login-screen">
    <div class="login-panel">
      <div>
        <p class="product-mark">Quant Lab</p>
        <h1>量化研究数据工作台</h1>
        <p class="subtle">登录后查看已录入标的，管理员可以通过 Tushare 同步行情数据。</p>
      </div>
      <el-form label-position="top" @submit.prevent="$emit('login')">
        <el-form-item label="账号">
          <el-input v-model="loginForm.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="loginForm.password" type="password" autocomplete="current-password" show-password />
        </el-form-item>
        <el-button type="primary" class="wide-button" :loading="loading" @click="$emit('login')">
          <LogIn :size="18" />
          登录
        </el-button>
      </el-form>
    </div>
  </section>
</template>

<script setup>
import { LogIn } from '@lucide/vue'

defineProps({
  loginForm: {
    type: Object,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['login'])
</script>

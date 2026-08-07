<template>
  <main class="app-shell">
    <!-- Quant Lab is moving from a single data page into a multi-user internal research platform.
    The data center remains the first module, while strategy/research-process modules should be designed with the user before implementation. -->
    <LoginScreen v-if="!token" :login-form="loginForm" :loading="authLoading" @login="login" />
    <AppShell
      v-else
      v-model:active-module="activeModule"
      :title="activeModuleTitle"
      :modules="moduleOptions"
      :user="user"
      :role-label="roleLabel"
      @logout="logout"
    >
      <DataCenterPage v-if="activeModule === 'data-center'" :token="token" :user="user" />
      <StrategyPage v-else-if="activeModule === 'strategy'" :token="token" :user="user" @open-backtest="openBacktest" />
      <BacktestPage
        v-else-if="activeModule === 'backtest'"
        :token="token"
        :target="backtestTarget"
        @back-to-strategy="activeModule = 'strategy'"
      />
    </AppShell>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppShell from './app/AppShell.vue'
import LoginScreen from './app/LoginScreen.vue'
import { useAuth } from './app/useAuth'
import BacktestPage from './modules/backtest/BacktestPage.vue'
import DataCenterPage from './modules/data-center/DataCenterPage.vue'
import StrategyPage from './modules/strategy/StrategyPage.vue'

const { token, user, loginForm, loading: authLoading, roleLabel, login, logout } = useAuth()

const activeModule = ref('data-center')
const backtestTarget = ref(null)
const moduleOptions = [
  { label: '数据中心', value: 'data-center' },
  { label: '策略库', value: 'strategy' },
  { label: '回测', value: 'backtest' }
]
const activeModuleTitle = computed(
  () => moduleOptions.find((item) => item.value === activeModule.value)?.label || 'Quant Lab'
)

function openBacktest(payload) {
  backtestTarget.value = payload
  activeModule.value = 'backtest'
}
</script>

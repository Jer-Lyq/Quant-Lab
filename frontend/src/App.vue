<template>
  <main class="app-shell">
    <!-- Quant Lab is moving from a single data page into a multi-user internal research platform.
    The data center remains the first module, while strategy/research-process modules should be designed with the user before implementation. -->
    <LoginScreen v-if="!token" :login-form="loginForm" :loading="authLoading" @login="login" />
    <AppShell v-else title="数据中心" :user="user" :role-label="roleLabel" @logout="logout">
      <DataCenterPage :token="token" :user="user" />
    </AppShell>
  </main>
</template>

<script setup>
import AppShell from './app/AppShell.vue'
import LoginScreen from './app/LoginScreen.vue'
import { useAuth } from './app/useAuth'
import DataCenterPage from './modules/data-center/DataCenterPage.vue'

const { token, user, loginForm, loading: authLoading, roleLabel, login, logout } = useAuth()
</script>

import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiRequest } from './apiClient'

const TOKEN_KEY = 'quant_lab_token'
const USER_KEY = 'quant_lab_user'

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function useAuth() {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref(readStoredUser())
  const loading = ref(false)
  const loginForm = ref({ username: 'admin', password: '' })
  const isAdmin = computed(() => user.value?.role === 'admin')
  const roleLabel = computed(() => (isAdmin.value ? '管理员' : '普通用户'))

  async function login() {
    loading.value = true
    try {
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginForm.value)
      })
      token.value = data.token
      user.value = data.user
      localStorage.setItem(TOKEN_KEY, data.token)
      localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    } catch (error) {
      ElMessage.error(error.message)
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return {
    token,
    user,
    loginForm,
    loading,
    isAdmin,
    roleLabel,
    login,
    logout
  }
}

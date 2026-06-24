import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import {
  changePassword as changePasswordApi,
  fetchCurrentUser,
  getAuthBootstrap,
  login as loginApi,
  registerFirstUser as registerFirstUserApi,
  updateProfile,
} from '@/api/auth'
import { clearStoredToken, getStoredToken, setStoredToken } from '@/api/authToken'
import type { AuthUser, ChangePasswordRequest, LoginRequest, RegisterRequest } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getStoredToken())
  const user = ref<AuthUser | null>(null)
  const registrationOpen = ref(false)
  const initialized = ref(false)
  const isLoading = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value && user.value))

  async function bootstrap() {
    const { data } = await getAuthBootstrap()
    registrationOpen.value = data.registration_open
    initialized.value = true
  }

  function setSession(accessToken: string, nextUser: AuthUser) {
    token.value = accessToken
    user.value = nextUser
    setStoredToken(accessToken)
  }

  async function registerFirstUser(payload: RegisterRequest) {
    isLoading.value = true
    try {
      const { data } = await registerFirstUserApi(payload)
      setSession(data.access_token, data.user)
      registrationOpen.value = false
    } finally {
      isLoading.value = false
    }
  }

  async function login(payload: LoginRequest) {
    isLoading.value = true
    try {
      const { data } = await loginApi(payload)
      setSession(data.access_token, data.user)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMe() {
    if (!token.value) return false
    try {
      const { data } = await fetchCurrentUser()
      user.value = data
      return true
    } catch {
      logout(false)
      return false
    }
  }

  async function updateUsername(username: string) {
    const { data } = await updateProfile({ username })
    user.value = data
    ElMessage.success('用户名已更新')
  }

  async function changePassword(payload: ChangePasswordRequest) {
    await changePasswordApi(payload)
    ElMessage.success('密码已更新')
  }

  function logout(showMessage = true) {
    token.value = null
    user.value = null
    clearStoredToken()
    if (showMessage) ElMessage.success('已退出登录')
  }

  return {
    token,
    user,
    registrationOpen,
    initialized,
    isLoading,
    isAuthenticated,
    bootstrap,
    registerFirstUser,
    login,
    fetchMe,
    updateUsername,
    changePassword,
    logout,
  }
})

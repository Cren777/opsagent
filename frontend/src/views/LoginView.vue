<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const form = reactive({ username: '', password: '' })

const title = computed(() => authStore.registrationOpen ? '创建首个管理员账号' : '登录 OpsAgent')
const buttonText = computed(() => authStore.registrationOpen ? '创建并进入' : '登录')
const passwordAutocomplete = computed(() => authStore.registrationOpen ? 'new-password' : 'current-password')

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '用户名长度需为 3-32 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码长度需为 8-128 个字符', trigger: 'blur' },
  ],
}

async function submit() {
  await formRef.value?.validate()
  try {
    if (authStore.registrationOpen) {
      await authStore.registerFirstUser(form)
    } else {
      await authStore.login(form)
    }
    router.push('/')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '认证失败')
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-panel">
      <div class="brand">
        <el-icon :size="28"><Monitor /></el-icon>
        <span>OpsAgent</span>
      </div>
      <h1>{{ title }}</h1>
      <p class="subtitle">智能运维助手访问入口</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名" prop="username">
          <el-input v-model.trim="form.username" autocomplete="username" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            :autocomplete="passwordAutocomplete"
            show-password
            size="large"
          />
        </el-form-item>
        <el-button type="primary" size="large" :loading="authStore.isLoading" class="submit-btn" @click="submit">
          {{ buttonText }}
        </el-button>
      </el-form>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 18% 12%, rgba(47, 125, 246, 0.14), transparent 30rem),
    linear-gradient(135deg, #eef4fb 0%, #f8fafc 100%);
}

.login-panel {
  width: min(420px, 100%);
  padding: 32px;
  background: #fff;
  border: 1px solid var(--ops-border);
  border-radius: 8px;
  box-shadow: var(--ops-shadow-md);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ops-primary);
  font-size: 20px;
  font-weight: 800;
  margin-bottom: 24px;
}

h1 {
  margin: 0 0 8px;
  font-size: 24px;
  color: var(--ops-text);
}

.subtitle {
  margin: 0 0 24px;
  color: var(--ops-text-secondary);
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}
</style>

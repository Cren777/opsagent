<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const form = reactive({ username: '' })
const isSaving = ref(false)

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '用户名长度需为 3-32 个字符', trigger: 'blur' },
  ],
}

watch(() => props.modelValue, (open) => {
  if (open) form.username = authStore.user?.username || ''
})

async function submit() {
  await formRef.value?.validate()
  isSaving.value = true
  try {
    await authStore.updateUsername(form.username)
    emit('update:modelValue', false)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="修改用户名" width="420px" @update:model-value="emit('update:modelValue', $event)">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="用户名" prop="username">
        <el-input v-model.trim="form.username" maxlength="32" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="isSaving" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

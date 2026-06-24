<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const isSaving = ref(false)
const form = reactive({ current_password: '', new_password: '', confirm_password: '' })

const rules: FormRules = {
  current_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码长度需为 8-128 个字符', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        value === form.new_password ? callback() : callback(new Error('两次输入的新密码不一致'))
      },
      trigger: 'blur',
    },
  ],
}

watch(() => props.modelValue, (open) => {
  if (!open) {
    form.current_password = ''
    form.new_password = ''
    form.confirm_password = ''
  }
})

async function submit() {
  await formRef.value?.validate()
  isSaving.value = true
  try {
    await authStore.changePassword({
      current_password: form.current_password,
      new_password: form.new_password,
    })
    emit('update:modelValue', false)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '修改失败')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="修改密码" width="420px" @update:model-value="emit('update:modelValue', $event)">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="当前密码" prop="current_password">
        <el-input v-model="form.current_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="form.new_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirm_password">
        <el-input v-model="form.confirm_password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="isSaving" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

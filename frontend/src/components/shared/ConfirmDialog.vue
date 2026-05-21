<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  title: string
  message: string
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const visible = ref(false)

function open() {
  visible.value = true
}

function close() {
  visible.value = false
}

function onConfirm() {
  emit('confirm')
  visible.value = false
}

defineExpose({ open, close })
</script>

<template>
  <el-dialog v-model="visible" :title="title" width="400px">
    <p>{{ message }}</p>
    <template #footer>
      <el-button @click="onConfirm" type="danger">确认</el-button>
      <el-button @click="close">取消</el-button>
    </template>
  </el-dialog>
</template>

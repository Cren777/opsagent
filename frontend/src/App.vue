<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from './components/layout/AppLayout.vue'

const route = useRoute()
const isPublicPage = computed(() => Boolean(route.meta.public))
</script>

<template>
  <router-view v-if="isPublicPage" />
  <AppLayout v-else />
</template>

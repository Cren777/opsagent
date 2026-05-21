import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DataSourceItem, DataSourceFormData, ConnectionTestResult } from '@/types/datasource'
import type { LLMProviderItem, LLMProviderFormData, LLMTestResult } from '@/types/llm'
import * as dsApi from '@/api/datasource'
import * as llmApi from '@/api/llm'

export const useConfigStore = defineStore('config', () => {
  // Data sources
  const dataSources = ref<DataSourceItem[]>([])
  const activeDataSource = ref<DataSourceItem | null>(null)

  async function fetchDataSources() {
    const { data } = await dsApi.fetchDataSources()
    dataSources.value = data
    activeDataSource.value = data.find((d) => d.is_active) || null
  }

  async function saveDataSource(form: DataSourceFormData, id?: string) {
    if (id) {
      const { data } = await dsApi.updateDataSource(id, form)
      const idx = dataSources.value.findIndex((d) => d.id === id)
      if (idx !== -1) dataSources.value[idx] = data
      return data
    } else {
      const { data } = await dsApi.createDataSource(form)
      dataSources.value.push(data)
      return data
    }
  }

  async function removeDataSource(id: string) {
    await dsApi.deleteDataSource(id)
    dataSources.value = dataSources.value.filter((d) => d.id !== id)
    if (activeDataSource.value?.id === id) {
      activeDataSource.value = null
    }
  }

  async function testConnection(id: string): Promise<ConnectionTestResult> {
    const { data } = await dsApi.testDataSource(id)
    return data
  }

  async function testNewConnection(form: DataSourceFormData): Promise<ConnectionTestResult> {
    const { data } = await dsApi.testNewDataSource(form)
    return data
  }

  async function activateSource(id: string) {
    await dsApi.activateDataSource(id)
    dataSources.value.forEach((d) => (d.is_active = d.id === id))
    activeDataSource.value = dataSources.value.find((d) => d.id === id) || null
  }

  // LLM providers
  const llmProviders = ref<LLMProviderItem[]>([])
  const primaryLLM = ref<LLMProviderItem | null>(null)

  async function fetchLLMProviders() {
    const { data } = await llmApi.fetchLLMProviders()
    llmProviders.value = data
    primaryLLM.value = data.find((p) => p.is_primary) || null
  }

  async function saveLLMProvider(form: LLMProviderFormData, id?: string) {
    if (id) {
      const { data } = await llmApi.updateLLMProvider(id, form)
      const idx = llmProviders.value.findIndex((p) => p.id === id)
      if (idx !== -1) llmProviders.value[idx] = data
      return data
    } else {
      const { data } = await llmApi.createLLMProvider(form)
      llmProviders.value.push(data)
      return data
    }
  }

  async function removeLLMProvider(id: string) {
    await llmApi.deleteLLMProvider(id)
    llmProviders.value = llmProviders.value.filter((p) => p.id !== id)
    if (primaryLLM.value?.id === id) {
      primaryLLM.value = llmProviders.value.find((p) => p.is_primary) || null
    }
  }

  async function testLLM(id: string, message: string): Promise<LLMTestResult> {
    const { data } = await llmApi.testLLMProvider(id, message)
    return data
  }

  async function testNewLLM(form: LLMProviderFormData, message: string): Promise<LLMTestResult> {
    const { data } = await llmApi.testNewLLMProvider({ ...form, message })
    return data
  }

  async function setPrimaryLLM(id: string) {
    await llmApi.setPrimaryLLMProvider(id)
    llmProviders.value.forEach((p) => (p.is_primary = p.id === id))
    primaryLLM.value = llmProviders.value.find((p) => p.id === id) || null
  }

  return {
    dataSources,
    activeDataSource,
    fetchDataSources,
    saveDataSource,
    removeDataSource,
    testConnection,
    testNewConnection,
    activateSource,
    llmProviders,
    primaryLLM,
    fetchLLMProviders,
    saveLLMProvider,
    removeLLMProvider,
    testLLM,
    testNewLLM,
    setPrimaryLLM,
  }
})

<script setup>
import { ref, onMounted } from 'vue'
import { eventApi } from '@/api'

const events = ref([])
const loading = ref(false)

async function loadEvents() {
  loading.value = true
  try {
    const data = await eventApi.list()
    events.value = data.results || data
  } catch {
    events.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadEvents)
</script>

<template>
  <el-card shadow="never">
    <template #header>事件记录</template>
    <el-timeline v-if="events.length" v-loading="loading">
      <el-timeline-item v-for="item in events" :key="item.id" :timestamp="item.created_at">
        {{ item.description }}
      </el-timeline-item>
    </el-timeline>
    <el-empty v-else description="暂无事件记录" />
  </el-card>
</template>

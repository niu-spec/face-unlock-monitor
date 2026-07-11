<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { homeApi, videoApi } from '@/api'
import { toZoneStreamId } from '@/constants/streams'

const props = defineProps({
  streamId: {
    type: String,
    default: '',
  },
})

const stats = ref({
  total: 0,
  family: 0,
  stranger: 0,
})

let timer = null

function applyPresence(data) {
  if (!data) return false
  stats.value = {
    total: data.total ?? data.total_count ?? 0,
    family: data.family ?? data.family_count ?? 0,
    stranger: data.stranger ?? data.stranger_count ?? 0,
  }
  return Boolean(data.updated_at)
}

async function fetchPresence() {
  const legacyId = props.streamId ? toZoneStreamId(props.streamId) : ''

  try {
    const videoStatus = await videoApi.status(props.streamId || undefined)
    if (applyPresence(videoStatus.presence)) return
  } catch {
    // fall through to legacy endpoint
  }

  try {
    const data = await homeApi.presence(legacyId || undefined)
    applyPresence(data)
  } catch {
    stats.value = { total: 0, family: 0, stranger: 0 }
  }
}

watch(
  () => props.streamId,
  () => {
    fetchPresence()
  },
)

onMounted(() => {
  fetchPresence()
  timer = window.setInterval(fetchPresence, 3000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <el-card shadow="never">
    <template #header>当前人数</template>
    <el-row :gutter="12">
      <el-col :span="8">
        <el-statistic title="总人数" :value="stats.total" />
      </el-col>
      <el-col :span="8">
        <el-statistic title="家人" :value="stats.family" />
      </el-col>
      <el-col :span="8">
        <el-statistic title="陌生人" :value="stats.stranger" />
      </el-col>
    </el-row>
  </el-card>
</template>

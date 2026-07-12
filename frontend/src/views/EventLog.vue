<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import EventReplayDialog from '@/components/EventReplayDialog.vue'
import { eventApi } from '@/api'

const POLL_MS = 3000
const events = ref([])
const loading = ref(false)
const lastUpdated = ref('')
const replayVisible = ref(false)
const replayItem = ref(null)
let pollTimer = null

async function loadEvents({ silent = false } = {}) {
  if (!silent) loading.value = true
  try {
    const data = await eventApi.list()
    events.value = data.results || data
    lastUpdated.value = new Date().toLocaleTimeString()
  } catch {
    if (!silent) events.value = []
  } finally {
    if (!silent) loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(() => loadEvents({ silent: true }), POLL_MS)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

function openReplay(item) {
  replayItem.value = item
  replayVisible.value = true
}

onMounted(() => {
  loadEvents()
  startPolling()
})

onBeforeUnmount(stopPolling)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="header">
        <div class="header-left">
          <span>事件记录</span>
          <span v-if="lastUpdated" class="refresh-meta">更新于 {{ lastUpdated }} · 每 {{ POLL_MS / 1000 }}s 自动刷新</span>
        </div>
        <el-button size="small" @click="loadEvents()">刷新</el-button>
      </div>
    </template>

    <el-table v-if="events.length" :data="events" stripe v-loading="loading">
      <el-table-column label="类型" width="140">
        <template #default="{ row }">{{ row.event_type_display || row.event_type }}</template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="220" />
      <el-table-column prop="stream_id" label="摄像头" width="120" />
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="回放" width="90">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            :disabled="!row.snapshot_path && !row.clip_path"
            @click="openReplay(row)"
          >
            回放
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else v-loading="loading" description="暂无事件记录" />

    <EventReplayDialog
      v-model="replayVisible"
      :title="replayItem?.event_type_display || '事件回放'"
      :description="replayItem?.description || ''"
      :timestamp="replayItem?.created_at || ''"
      :stream-id="replayItem?.stream_id || ''"
      :snapshot-path="replayItem?.snapshot_path || ''"
      :clip-path="replayItem?.clip_path || ''"
    />
  </el-card>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.refresh-meta {
  color: #909399;
  font-size: 12px;
}
</style>

<script setup>
import { ref, onMounted } from 'vue'
import EventReplayDialog from '@/components/EventReplayDialog.vue'
import { eventApi } from '@/api'

const events = ref([])
const loading = ref(false)
const replayVisible = ref(false)
const replayItem = ref(null)

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

function openReplay(item) {
  replayItem.value = item
  replayVisible.value = true
}

onMounted(loadEvents)
</script>

<template>
  <el-card shadow="never">
    <template #header>事件记录</template>

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
            :disabled="!row.snapshot_path"
            @click="openReplay(row)"
          >
            回放
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="暂无事件记录" />

    <EventReplayDialog
      v-model="replayVisible"
      :title="replayItem?.event_type_display || '事件回放'"
      :description="replayItem?.description || ''"
      :timestamp="replayItem?.created_at || ''"
      :stream-id="replayItem?.stream_id || ''"
      :snapshot-path="replayItem?.snapshot_path || ''"
    />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import EventReplayDialog from '@/components/EventReplayDialog.vue'
import { alertApi } from '@/api'

const filterType = ref('')
const alerts = ref([])
const loading = ref(false)
const replayVisible = ref(false)
const replayItem = ref(null)

const typeOptions = [
  { label: '全部', value: '' },
  { label: '陌生人', value: 'FACE_UNKNOWN' },
  { label: '区域闯入', value: 'INTRUSION' },
  { label: '距离过近', value: 'PROXIMITY' },
  { label: '异常停留', value: 'LOITER' },
  { label: '尾随进入', value: 'TAILGATE' },
  { label: '火情', value: 'FIRE' },
  { label: '积水', value: 'WATER' },
  { label: '人员摔倒', value: 'FALL' },
]

async function loadAlerts() {
  loading.value = true
  try {
    const params = filterType.value ? { type: filterType.value } : {}
    const data = await alertApi.list(params)
    alerts.value = data.results || data
  } catch {
    alerts.value = []
  } finally {
    loading.value = false
  }
}

async function handleAlert(alert) {
  try {
    await alertApi.handle(alert.id)
    ElMessage.success('已处置')
    loadAlerts()
  } catch {
    /* ignore */
  }
}

function openReplay(alert) {
  replayItem.value = alert
  replayVisible.value = true
}

onMounted(loadAlerts)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="header">
        <span>告警中心</span>
        <el-select v-model="filterType" placeholder="按类型筛选" style="width: 180px" @change="loadAlerts">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </div>
    </template>

    <el-table v-if="alerts.length" :data="alerts" stripe v-loading="loading">
      <el-table-column label="类型" width="120">
        <template #default="{ row }">{{ row.type_display || row.type }}</template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" />
      <el-table-column label="等级" width="80">
        <template #default="{ row }">
          <el-tag :type="row.level === 'HIGH' ? 'danger' : row.level === 'MEDIUM' ? 'warning' : 'info'" size="small">
            {{ row.level_display || row.level }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="通知状态" width="110">
        <template #default="{ row }">
          <template v-if="!row.notified_at">
            <el-tag size="small" type="info">未通知</el-tag>
          </template>
          <template v-else-if="row.escalation_level > 0">
            <el-tag size="small" type="warning">已升级 Lv.{{ row.escalation_level }}</el-tag>
          </template>
          <template v-else>
            <el-tag size="small" type="success">已通知</el-tag>
          </template>
        </template>
      </el-table-column>
      <el-table-column label="负责人" width="120">
        <template #default="{ row }">
          <span v-if="row.assigned_to_name">{{ row.assigned_to_name }}</span>
          <span v-else style="color:#999">-</span>
        </template>
      </el-table-column>
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
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" link type="primary" @click="handleAlert(row)">处置</el-button>
          <el-tag v-else size="small" type="success">已处理</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="暂无告警" />

    <EventReplayDialog
      v-model="replayVisible"
      :title="replayItem?.type_display || '告警回放'"
      :description="replayItem?.description || ''"
      :timestamp="replayItem?.created_at || ''"
      :stream-id="replayItem?.stream_id || ''"
      :snapshot-path="replayItem?.snapshot_path || ''"
    />
  </el-card>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>

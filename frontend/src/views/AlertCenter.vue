<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import EventReplayDialog from '@/components/EventReplayDialog.vue'
import { alertApi, videoApi } from '@/api'

const POLL_MS = 3000
const filterType = ref('')
const filterStatus = ref('pending')
const alerts = ref([])
const loading = ref(false)
const lastUpdated = ref('')
const pipelineHint = ref('')
const replayVisible = ref(false)
const replayItem = ref(null)
let pollTimer = null

const typeOptions = [
  { label: '全部', value: '' },
  { label: '陌生人', value: 'FACE_UNKNOWN' },
  { label: '人脸欺骗攻击', value: 'FACE_SPOOF' },
  { label: '照片/视频重放', value: 'FACE_REPLAY' },
  { label: 'AI换脸攻击', value: 'FACE_DEEPFAKE' },
  { label: '人脸认证失败', value: 'FACE_AUTH_FAILED' },
  { label: '区域闯入', value: 'INTRUSION' },
  { label: '距离过近', value: 'PROXIMITY' },
  { label: '异常停留', value: 'LOITER' },
  { label: '尾随进入', value: 'TAILGATE' },
  { label: '火情', value: 'FIRE' },
  { label: '积水', value: 'WATER' },
  { label: '人员摔倒', value: 'FALL' },
  { label: '尖叫/呼救', value: 'SCREAM' },
  { label: '打架/争吵', value: 'FIGHT' },
  { label: '哭喊声', value: 'CRYING' },
  { label: '玻璃破碎', value: 'GLASS_BREAK' },
  { label: '异常声音', value: 'ABNORMAL_SOUND' },
  { label: '联动紧急', value: 'EMERGENCY' },
]

async function loadAlerts({ silent = false } = {}) {
  if (!silent) loading.value = true
  try {
    const params = {}
    if (filterType.value) params.type = filterType.value
    if (filterStatus.value) params.status = filterStatus.value
    const data = await alertApi.list(params)
    alerts.value = data.results || data
    lastUpdated.value = new Date().toLocaleTimeString()
  } catch {
    if (!silent) alerts.value = []
  } finally {
    if (!silent) loading.value = false
  }
}

async function checkPipeline() {
  try {
    const data = await videoApi.status()
    const workers = data.workers || {}
    const active = Object.values(workers).filter((w) => w?.has_frame).length
    const total = Object.keys(workers).length
    if (active > 0) {
      pipelineHint.value = `视频 AI 运行中（${active}/${total || active} 路有画面）`
      return
    }
    if (total > 0) {
      pipelineHint.value = '视频 worker 已启动但未收到画面，请确认 RTSP 推流正常，并先在「居家监控」打开对应摄像头'
      return
    }
    pipelineHint.value = '视频 AI 未启动，请先在「居家监控」页面打开摄像头以启动检测'
  } catch {
    pipelineHint.value = ''
  }
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(() => {
    loadAlerts({ silent: true })
    if (alerts.value.length === 0) checkPipeline()
  }, POLL_MS)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
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

async function ignoreAlert(alert) {
  try {
    await ElMessageBox.confirm('确认忽略该告警？忽略后不再参与升级通知。', '忽略告警', {
      type: 'warning',
      confirmButtonText: '忽略',
      cancelButtonText: '取消',
    })
    await alertApi.ignore(alert.id)
    ElMessage.success('已忽略')
    loadAlerts()
  } catch (err) {
    if (err !== 'cancel') {
      /* request failed */
    }
  }
}

function openReplay(alert) {
  replayItem.value = alert
  replayVisible.value = true
}

onMounted(async () => {
  await Promise.all([loadAlerts(), checkPipeline()])
  startPolling()
})

onBeforeUnmount(stopPolling)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="header">
        <div class="header-left">
          <span>告警中心</span>
          <span v-if="lastUpdated" class="refresh-meta">更新于 {{ lastUpdated }} · 每 {{ POLL_MS / 1000 }}s 自动刷新</span>
        </div>
        <div class="header-actions">
          <el-button size="small" @click="loadAlerts()">刷新</el-button>
          <el-select v-model="filterStatus" placeholder="按状态筛选" style="width: 120px" @change="loadAlerts()">
            <el-option v-for="item in statusOptions" :key="item.value || 'all'" :label="item.label" :value="item.value" />
          </el-select>
          <el-select v-model="filterType" placeholder="按类型筛选" style="width: 200px" @change="loadAlerts()">
            <el-option v-for="item in typeOptions" :key="item.value || 'all-types'" :label="item.label" :value="item.value" />
          </el-select>
        </div>
      </div>
    </template>

    <el-alert
      v-if="pipelineHint && alerts.length === 0"
      :title="pipelineHint"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 12px"
    />

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
            :disabled="!row.snapshot_path && !row.clip_path"
            @click="openReplay(row)"
          >
            回放
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'pending'" size="small" type="warning">待处理</el-tag>
          <el-tag v-else-if="row.status === 'ignored'" size="small" type="info">已忽略</el-tag>
          <el-tag v-else size="small" type="success">已处理</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button link type="primary" @click="handleAlert(row)">处置</el-button>
            <el-button link type="info" @click="ignoreAlert(row)">忽略</el-button>
          </template>
          <span v-else style="color:#999">-</span>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else v-loading="loading" description="暂无告警" />

    <EventReplayDialog
      v-model="replayVisible"
      :title="replayItem?.type_display || '告警回放'"
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.refresh-meta {
  color: #909399;
  font-size: 12px;
}
</style>

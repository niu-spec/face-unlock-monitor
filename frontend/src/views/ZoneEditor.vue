<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FaceOverlay from '@/components/FaceOverlay.vue'
import { zoneApi, videoApi, webrtcPreviewUrl } from '@/api'
import {
  CAMERA_STREAMS,
  DEFAULT_STREAM_ID,
  toZoneStreamId,
} from '@/constants/streams'

const POLL_MS = 200

const CANVAS_W = 640
const CANVAS_H = 480

const zones = ref([])
const loading = ref(false)
const saving = ref(false)
const activeStream = ref(DEFAULT_STREAM_ID)
const editingId = ref(null)
const draftPoints = ref([])
const canvasRef = ref(null)
const streamPresence = ref(null)

let pollTimer = null
let fetchingPresence = false

const form = reactive({
  name: '',
  forbidden_roles: ['child', 'stranger'],
  safe_distance: 50,
  dwell_time: 5,
})

const roleOptions = [
  { label: '小孩', value: 'child' },
  { label: '成人', value: 'adult' },
  { label: '老人', value: 'elder' },
  { label: '访客', value: 'guest' },
  { label: '陌生人', value: 'stranger' },
]

const activeZoneStreamId = computed(() => toZoneStreamId(activeStream.value))

const streamZones = computed(() =>
  zones.value.filter((z) => z.stream_id === activeZoneStreamId.value),
)

const webrtcUrl = computed(() => webrtcPreviewUrl(activeStream.value))

async function refreshPresence() {
  if (fetchingPresence) return
  fetchingPresence = true
  try {
    const data = await videoApi.presence(activeStream.value)
    streamPresence.value = data.presence || null
  } catch {
    /* keep last snapshot */
  } finally {
    fetchingPresence = false
  }
}

function startPresencePolling() {
  stopPresencePolling()
  refreshPresence()
  pollTimer = window.setInterval(refreshPresence, POLL_MS)
}

function stopPresencePolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

async function loadZones() {
  loading.value = true
  try {
    const data = await zoneApi.list()
    zones.value = data.results || data
  } catch {
    zones.value = []
  } finally {
    loading.value = false
    await nextTick()
    redrawCanvas()
  }
}

function resetForm() {
  editingId.value = null
  form.name = activeStream.value === '2' ? '厨房禁区' : '客厅禁区'
  form.forbidden_roles = ['child', 'stranger']
  form.safe_distance = 50
  form.dwell_time = 5
  draftPoints.value = []
}

function startNewZone() {
  resetForm()
  redrawCanvas()
}

function selectZone(zone) {
  editingId.value = zone.id
  form.name = zone.name
  form.forbidden_roles = [...(zone.forbidden_roles || [])]
  form.safe_distance = zone.safe_distance ?? 50
  form.dwell_time = zone.dwell_time ?? 5
  draftPoints.value = (zone.points_json || []).map((p) => [...p])
  redrawCanvas()
}

function getCanvasPoint(event) {
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const scaleX = CANVAS_W / rect.width
  const scaleY = CANVAS_H / rect.height
  return {
    x: Math.round((event.clientX - rect.left) * scaleX),
    y: Math.round((event.clientY - rect.top) * scaleY),
  }
}

function onCanvasClick(event) {
  const { x, y } = getCanvasPoint(event)
  draftPoints.value.push([x, y])
  redrawCanvas()
}

function undoPoint() {
  if (draftPoints.value.length === 0) return
  draftPoints.value.pop()
  redrawCanvas()
}

function clearDraft() {
  draftPoints.value = []
  redrawCanvas()
}

function drawPolygon(ctx, points, options = {}) {
  if (!points || points.length < 2) return
  const {
    stroke = '#409eff',
    fill = 'rgba(64, 158, 255, 0.2)',
    lineWidth = 2,
    dashed = false,
    showVertices = false,
  } = options

  ctx.beginPath()
  ctx.moveTo(points[0][0], points[0][1])
  for (let i = 1; i < points.length; i += 1) {
    ctx.lineTo(points[i][0], points[i][1])
  }
  if (points.length >= 3) {
    ctx.closePath()
    ctx.fillStyle = fill
    ctx.fill()
  }
  ctx.strokeStyle = stroke
  ctx.lineWidth = lineWidth
  ctx.setLineDash(dashed ? [6, 4] : [])
  ctx.stroke()
  ctx.setLineDash([])

  if (!showVertices) return

  points.forEach(([x, y], index) => {
    ctx.beginPath()
    ctx.arc(x, y, 4, 0, Math.PI * 2)
    ctx.fillStyle = stroke
    ctx.fill()
    ctx.fillStyle = '#fff'
    ctx.font = '12px sans-serif'
    ctx.fillText(String(index + 1), x + 6, y - 6)
  })
}

function redrawCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, CANVAS_W, CANVAS_H)

  streamZones.value.forEach((zone) => {
    const isEditing = zone.id === editingId.value
    const points = isEditing && draftPoints.value.length >= 3
      ? draftPoints.value
      : zone.points_json

    drawPolygon(ctx, points, {
      stroke: '#f56c6c',
      fill: 'rgba(245, 108, 108, 0.22)',
      lineWidth: isEditing ? 2.5 : 2,
    })
  })

  if (!editingId.value && draftPoints.value.length > 0) {
    drawPolygon(ctx, draftPoints.value, {
      stroke: '#409eff',
      fill: 'rgba(64, 158, 255, 0.18)',
      dashed: draftPoints.value.length < 3,
      showVertices: true,
    })
  }
}

async function onSave() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入区域名称')
    return
  }
  if (draftPoints.value.length < 3) {
    ElMessage.warning('请在画布上至少点击 3 个点构成多边形')
    return
  }
  if (form.forbidden_roles.length === 0) {
    ElMessage.warning('请至少选择一个禁止角色')
    return
  }

  const payload = {
    name: form.name.trim(),
    stream_id: activeZoneStreamId.value,
    points_json: draftPoints.value.map((p) => [...p]),
    forbidden_roles: [...form.forbidden_roles],
    safe_distance: form.safe_distance,
    dwell_time: form.dwell_time,
    is_active: true,
  }

  saving.value = true
  try {
    if (editingId.value) {
      await zoneApi.update(editingId.value, payload)
      ElMessage.success('区域已更新')
    } else {
      await zoneApi.create(payload)
      ElMessage.success('区域已创建')
    }
    await loadZones()
    startNewZone()
    await nextTick()
    redrawCanvas()
  } catch {
    /* handled by interceptor */
  } finally {
    saving.value = false
  }
}

async function onDelete(zone) {
  try {
    await ElMessageBox.confirm(`确定删除区域「${zone.name}」？`, '删除确认', {
      type: 'warning',
    })
    await zoneApi.remove(zone.id)
    ElMessage.success('已删除')
    if (editingId.value === zone.id) startNewZone()
    await loadZones()
  } catch {
    /* cancel or error */
  }
}

watch(activeStream, () => {
  startNewZone()
  streamPresence.value = null
  startPresencePolling()
})

onMounted(async () => {
  startNewZone()
  await loadZones()
  startPresencePolling()
})

onBeforeUnmount(() => {
  stopPresencePolling()
})
</script>

<template>
  <el-row :gutter="16">
    <el-col :span="16">
      <el-alert
        class="zone-hint"
        type="info"
        :closable="false"
        show-icon
        title="保存后蓝色绘制框会消失，红色区域为已生效禁区。Canvas 会叠加人物/人脸/闯入等检测框，便于对照区域是否生效。"
      />
      <el-card shadow="never">
        <template #header>
          <div class="header">
            <span>危险区域画框</span>
            <el-radio-group v-model="activeStream" size="small">
              <el-radio-button v-for="item in CAMERA_STREAMS" :key="item.id" :value="item.id">
                {{ item.label }}（流 {{ item.id }}）
              </el-radio-button>
            </el-radio-group>
          </div>
        </template>

        <div class="canvas-wrap">
          <iframe
            :key="`webrtc-${activeStream}`"
            :src="webrtcUrl"
            class="video-bg"
            title="摄像头画面"
            allow="autoplay; fullscreen"
          />
          <FaceOverlay
            :key="`overlay-${activeStream}`"
            :stream-id="activeStream"
            :presence="streamPresence"
            :show-recognition-boxes="false"
            managed-externally
            active
          />
          <canvas
            ref="canvasRef"
            class="draw-canvas"
            :width="CANVAS_W"
            :height="CANVAS_H"
            @click="onCanvasClick"
          />
        </div>

        <div class="canvas-tools">
          <el-text type="info">点击画布添加顶点，至少 3 个点后保存</el-text>
          <div class="tool-actions">
            <el-button size="small" :disabled="draftPoints.length === 0" @click="undoPoint">
              撤销顶点
            </el-button>
            <el-button size="small" :disabled="draftPoints.length === 0" @click="clearDraft">
              清空绘制
            </el-button>
          </div>
        </div>
      </el-card>
    </el-col>

    <el-col :span="8">
      <el-card shadow="never" class="form-card">
        <template #header>
          <div class="header">
            <span>{{ editingId ? '编辑区域' : '新建区域' }}</span>
            <el-button text type="primary" @click="startNewZone">新建</el-button>
          </div>
        </template>

        <el-form label-width="88px">
          <el-form-item label="区域名称">
            <el-input v-model="form.name" placeholder="如：厨房禁区" />
          </el-form-item>
          <el-form-item label="禁止角色">
            <el-checkbox-group v-model="form.forbidden_roles">
              <el-checkbox v-for="item in roleOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="安全距离">
            <el-input-number v-model="form.safe_distance" :min="10" :max="300" />
            <el-text type="info" size="small" style="margin-left: 8px">px</el-text>
          </el-form-item>
          <el-form-item label="停留阈值">
            <el-input-number v-model="form.dwell_time" :min="1" :max="120" />
            <el-text type="info" size="small" style="margin-left: 8px">秒</el-text>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="onSave">
              {{ editingId ? '保存修改' : '保存区域' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="list-card">
        <template #header>
          <span>当前画面区域（{{ streamZones.length }}）</span>
        </template>

        <el-table
          v-if="streamZones.length"
          v-loading="loading"
          :data="streamZones"
          stripe
          size="small"
          highlight-current-row
          @row-click="selectZone"
        >
          <el-table-column prop="name" label="名称" />
          <el-table-column label="禁止角色" width="100">
            <template #default="{ row }">
              {{ (row.forbidden_roles || []).join(', ') || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70">
            <template #default="{ row }">
              <el-button link type="danger" @click.stop="onDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无区域，请在左侧画布绘制" />
      </el-card>
    </el-col>
  </el-row>
</template>

<style scoped>
.zone-hint {
  margin-bottom: 12px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.canvas-wrap {
  position: relative;
  width: 100%;
  max-width: 640px;
  aspect-ratio: 4 / 3;
  margin: 0 auto;
  background: #1a1a1a;
  border-radius: 8px;
  overflow: hidden;
}

.video-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
  pointer-events: none;
}

.draw-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  cursor: crosshair;
  z-index: 3;
}

.canvas-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  gap: 12px;
}

.tool-actions {
  display: flex;
  gap: 8px;
}

.form-card {
  margin-bottom: 16px;
}

.list-card :deep(.el-table__row) {
  cursor: pointer;
}
</style>

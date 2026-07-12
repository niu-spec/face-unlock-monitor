<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import FaceOverlay from '@/components/FaceOverlay.vue'
import PersonStats from '@/components/PersonStats.vue'
import { videoApi, webrtcPreviewUrl } from '@/api'
import { CAMERA_STREAMS, DEFAULT_STREAM_ID, toZoneStreamId } from '@/constants/streams'

const POLL_MS = 200

const activeStream = ref(DEFAULT_STREAM_ID)
const streamPresence = ref(null)
const streamLive = ref(true)
const livenessByStream = ref({})

const webrtcUrl = computed(() => webrtcPreviewUrl(activeStream.value))
const activeLiveness = computed(() => livenessByStream.value[toZoneStreamId(activeStream.value)] || null)
const livenessTag = computed(() => {
  const status = activeLiveness.value?.status
  if (status === 'passed') return { type: 'success', text: '活体通过' }
  if (status === 'attack') return { type: 'danger', text: '疑似欺骗' }
  if (status === 'insufficient') return { type: 'warning', text: '活体采样中' }
  return { type: 'info', text: '活体未知' }
})

let pollTimer = null
let fetching = false

function openWebRtcWindow() {
  window.open(webrtcUrl.value, '_blank', 'noopener,noreferrer')
}

async function refreshStreamData() {
  if (fetching) return
  fetching = true
  try {
    let data
    try {
      data = await videoApi.presence(activeStream.value)
    } catch {
      data = await videoApi.status(activeStream.value)
    }
    streamPresence.value = data.presence || null
    streamLive.value = data.stream_live !== false
    const legacyId = toZoneStreamId(activeStream.value)
    const liveness = data.liveness
    if (legacyId && liveness) {
      const entry = typeof liveness === 'object' && 'status' in liveness
        ? liveness
        : liveness[legacyId]
      if (entry) {
        livenessByStream.value = {
          ...livenessByStream.value,
          [legacyId]: entry,
        }
      }
    }
  } catch {
    /* keep the last snapshot */
  } finally {
    fetching = false
  }
}

function startPolling() {
  stopPolling()
  refreshStreamData()
  pollTimer = window.setInterval(refreshStreamData, POLL_MS)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(activeStream, () => {
  streamPresence.value = null
  streamLive.value = true
  startPolling()
})

onMounted(() => {
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <div class="monitor-page">
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>实时画面</span>
              <div class="header-actions">
                <el-tag v-if="!streamLive" type="info" effect="plain" size="small">
                  无推流信号
                </el-tag>
                <el-tag :type="livenessTag.type" effect="plain" size="small">
                  {{ livenessTag.text }}
                </el-tag>
                <el-radio-group v-model="activeStream" size="small">
                  <el-radio-button v-for="item in CAMERA_STREAMS" :key="item.id" :value="item.id">
                    {{ item.label }}
                  </el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>

          <div class="video-box">
            <iframe
              :key="`webrtc-${activeStream}`"
              :src="webrtcUrl"
              title="WebRTC 实时画面"
              allow="autoplay; fullscreen"
              class="video-frame"
            />
            <FaceOverlay
              :key="`overlay-${activeStream}`"
              :stream-id="activeStream"
              :presence="streamPresence"
              managed-externally
              active
            />
          </div>

          <div class="video-footer">
            <span class="video-hint">
              低延迟 WebRTC 预览 · AI 人脸标注由 Canvas 叠加（后端 RTSP 检测）
            </span>
            <el-button
              link
              type="primary"
              size="small"
              @click="openWebRtcWindow"
            >
              新窗口打开
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <PersonStats :stream-id="activeStream" :presence="streamPresence" managed-externally />
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.video-box {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 420px;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-frame {
  width: 100%;
  height: 480px;
  border: none;
  object-fit: contain;
  background: #000;
}

.video-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  gap: 8px;
}

.video-hint {
  color: #909399;
  font-size: 12px;
}
</style>

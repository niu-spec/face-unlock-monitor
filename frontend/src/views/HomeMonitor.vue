<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import FaceOverlay from '@/components/FaceOverlay.vue'
import PersonStats from '@/components/PersonStats.vue'
import { videoApi, videoFeedUrl, webrtcPreviewUrl } from '@/api'
import { CAMERA_STREAMS, DEFAULT_STREAM_ID, toZoneStreamId } from '@/constants/streams'

const activeStream = ref(DEFAULT_STREAM_ID)
const previewMode = ref('webrtc')
const videoError = ref(false)
const livenessByStream = ref({})

const webrtcUrl = computed(() => webrtcPreviewUrl(activeStream.value))
const mjpegUrl = computed(() => videoFeedUrl(activeStream.value))
const activeLiveness = computed(() => livenessByStream.value[toZoneStreamId(activeStream.value)] || null)
const livenessTag = computed(() => {
  const status = activeLiveness.value?.status
  if (status === 'passed') return { type: 'success', text: '活体通过' }
  if (status === 'attack') return { type: 'danger', text: '疑似欺骗' }
  if (status === 'insufficient') return { type: 'warning', text: '活体采样中' }
  return { type: 'info', text: '活体未知' }
})

let statusTimer = null

function onVideoError() {
  videoError.value = true
}

function onVideoLoad() {
  videoError.value = false
}

function openWebRtcWindow() {
  window.open(webrtcUrl.value, '_blank', 'noopener,noreferrer')
}

async function refreshVideoStatus() {
  try {
    const data = await videoApi.status()
    livenessByStream.value = data.liveness || {}
  } catch {
    /* keep the last liveness status */
  }
}

onMounted(() => {
  refreshVideoStatus()
  statusTimer = window.setInterval(refreshVideoStatus, 3000)
})

onBeforeUnmount(() => {
  if (statusTimer) window.clearInterval(statusTimer)
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
                <el-tag :type="livenessTag.type" effect="plain" size="small">
                  {{ livenessTag.text }}
                </el-tag>
                <el-radio-group v-model="activeStream" size="small">
                  <el-radio-button v-for="item in CAMERA_STREAMS" :key="item.id" :value="item.id">
                    {{ item.label }}
                  </el-radio-button>
                </el-radio-group>
                <el-radio-group v-model="previewMode" size="small">
                  <el-radio-button value="webrtc">WebRTC</el-radio-button>
                  <el-radio-button value="mjpeg">MJPEG 备用</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>

          <div class="video-box">
            <iframe
              v-if="previewMode === 'webrtc'"
              :key="`webrtc-${activeStream}`"
              :src="webrtcUrl"
              title="WebRTC 实时画面"
              allow="autoplay; fullscreen"
              class="video-frame"
            />
            <FaceOverlay
              v-if="previewMode === 'webrtc'"
              :key="`overlay-${activeStream}`"
              :stream-id="activeStream"
              :active="previewMode === 'webrtc'"
            />
            <img
              v-else
              :key="`mjpeg-${activeStream}`"
              :src="mjpegUrl"
              alt="MJPEG 实时画面"
              class="video-frame"
              @error="onVideoError"
              @load="onVideoLoad"
            />
            <div v-if="previewMode === 'mjpeg' && videoError" class="video-fallback">
              视频流未就绪（推流码 {{ activeStream }}）<br />
              请确认 MediaMTX 与 OBS 已启动，或切换回 WebRTC 预览
            </div>
          </div>

          <div class="video-footer">
            <span v-if="previewMode === 'webrtc'" class="video-hint">
              低延迟 WebRTC 预览 · 含 AI 人脸标注（Canvas 叠加）
            </span>
            <span v-else class="video-hint">
              MJPEG 备用预览（延迟较高，含 AI 标注框）
            </span>
            <el-button
              v-if="previewMode === 'webrtc'"
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
        <PersonStats />
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

.video-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  text-align: center;
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
  background: rgba(0, 0, 0, 0.65);
  pointer-events: none;
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

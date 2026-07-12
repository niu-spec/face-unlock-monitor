<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { isMobileDevice } from '@/utils/device'

const emit = defineEmits(['capture', 'capture-sequence'])

const videoRef = ref(null)
const streaming = ref(false)
const capturing = ref(false)
const sequenceCapturing = ref(false)
const facingMode = ref('user')
const isMobile = ref(false)

let mediaStream = null

const mirrorPreview = computed(() => facingMode.value === 'user')

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    ElMessage.error('当前浏览器不支持摄像头')
    return
  }

  try {
    stopCamera()
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: facingMode.value },
        width: { ideal: isMobile.value ? 1280 : 640 },
        height: { ideal: isMobile.value ? 720 : 480 },
      },
      audio: false,
    })
    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
      await videoRef.value.play()
    }
    streaming.value = true
  } catch {
    ElMessage.error('无法打开摄像头，请检查浏览器权限')
    streaming.value = false
  }
}

function stopCamera() {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  streaming.value = false
}

function switchCamera() {
  facingMode.value = facingMode.value === 'user' ? 'environment' : 'user'
  startCamera()
}

function grabFrameFile() {
  const video = videoRef.value
  if (!video || !streaming.value) return Promise.reject(new Error('camera not ready'))

  const width = video.videoWidth
  const height = video.videoHeight
  if (!width || !height) return Promise.reject(new Error('video not ready'))

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return Promise.reject(new Error('canvas not available'))

  if (mirrorPreview.value) {
    ctx.translate(width, 0)
    ctx.scale(-1, 1)
  }
  ctx.drawImage(video, 0, 0, width, height)

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error('capture failed'))
          return
        }
        const previewUrl = URL.createObjectURL(blob)
        const file = new File([blob], `capture_${Date.now()}.jpg`, { type: 'image/jpeg' })
        resolve({ file, previewUrl })
      },
      'image/jpeg',
      0.92,
    )
  })
}

async function captureFrame() {
  if (capturing.value || sequenceCapturing.value) return

  capturing.value = true
  try {
    const payload = await grabFrameFile()
    emit('capture', payload)
    ElMessage.success('已截取当前画面')
  } catch (err) {
    ElMessage.warning(err.message === 'video not ready' ? '摄像头画面未就绪，请稍候再试' : '截图失败')
  } finally {
    capturing.value = false
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function captureSequence(count = 4) {
  if (capturing.value || sequenceCapturing.value) return

  sequenceCapturing.value = true
  const files = []
  let previewUrl = ''
  try {
    for (let index = 0; index < count; index += 1) {
      const payload = await grabFrameFile()
      files.push(payload.file)
      if (previewUrl) URL.revokeObjectURL(previewUrl)
      previewUrl = payload.previewUrl
      if (index < count - 1) await sleep(350)
    }
    emit('capture-sequence', { files, previewUrl })
    ElMessage.success(`已连续采集 ${files.length} 帧`)
  } catch {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    ElMessage.error('连续采集失败，请保持人脸在画面中')
  } finally {
    sequenceCapturing.value = false
  }
}

onMounted(() => {
  isMobile.value = isMobileDevice()
  facingMode.value = isMobile.value ? 'environment' : 'user'
  startCamera()
})

onBeforeUnmount(stopCamera)

defineExpose({ startCamera, stopCamera, captureFrame, captureSequence, switchCamera })
</script>

<template>
  <div class="face-capture" :class="{ mobile: isMobile }">
    <el-alert
      v-if="isMobile"
      title="请对准面部，建议使用「连续采集 4 帧」完成活体检测"
      type="info"
      :closable="false"
      show-icon
      class="mobile-tip"
    />
    <div class="camera-box">
      <video
        ref="videoRef"
        class="camera-video"
        :class="{ mirror: mirrorPreview }"
        playsinline
        webkit-playsinline
        muted
      />
      <div v-if="!streaming" class="camera-placeholder">正在启动摄像头...</div>
    </div>
    <div class="camera-actions">
      <el-button @click="startCamera">重新打开</el-button>
      <el-button v-if="isMobile" @click="switchCamera">
        {{ facingMode === 'environment' ? '切换前置' : '切换后置' }}
      </el-button>
      <el-button type="primary" :loading="capturing" :disabled="!streaming" @click="captureFrame">
        截取当前画面
      </el-button>
      <el-button
        type="success"
        :loading="sequenceCapturing"
        :disabled="!streaming"
        @click="captureSequence"
      >
        连续采集 4 帧
      </el-button>
    </div>
    <p class="camera-hint">
      {{ isMobile ? '请对准家人面部，按提示轻微转头或眨眼，确保只有一张人脸。' : '建议使用连续采集完成活体检测；只上传静态照片可能无法通过注册。' }}
    </p>
  </div>
</template>

<style scoped>
.face-capture {
  width: 100%;
}

.face-capture.mobile .camera-box {
  width: 100%;
  max-width: 480px;
}

.mobile-tip {
  margin-bottom: 12px;
}

.camera-box {
  position: relative;
  width: 320px;
  max-width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: 8px;
  overflow: hidden;
  background: #000;
  border: 1px solid var(--el-border-color);
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-video.mirror {
  transform: scaleX(-1);
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 13px;
  background: rgba(0, 0, 0, 0.55);
}

.camera-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.camera-hint {
  margin: 8px 0 0;
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
}
</style>

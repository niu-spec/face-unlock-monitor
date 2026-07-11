<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { videoApi } from '@/api'
import { toZoneStreamId } from '@/constants/streams'

const props = defineProps({
  streamId: {
    type: String,
    required: true,
  },
  active: {
    type: Boolean,
    default: true,
  },
})

const POLL_MS = 600
const DEFAULT_FRAME = { width: 1280, height: 720 }

const canvasRef = ref(null)
let pollTimer = null
let resizeObserver = null
let faces = []
let frameSize = { ...DEFAULT_FRAME }

function getContainer() {
  return canvasRef.value?.parentElement ?? null
}

function faceLabel(face) {
  if (face.trusted === false) return '疑似欺骗'
  if (!face.known) return '陌生人'
  const roleLabels = { adult: '成人', child: '儿童' }
  const role = roleLabels[face.role] || face.role || '家人'
  const name = (face.name || '').trim() || '家人'
  return `${name} (${role})`
}

function computeVideoRect(containerW, containerH, videoW, videoH) {
  if (!containerW || !containerH || !videoW || !videoH) {
    return { x: 0, y: 0, width: containerW, height: containerH, scaleX: 1, scaleY: 1 }
  }

  const videoAspect = videoW / videoH
  const containerAspect = containerW / containerH

  if (containerAspect > videoAspect) {
    const height = containerH
    const width = containerH * videoAspect
    return {
      x: (containerW - width) / 2,
      y: 0,
      width,
      height,
      scaleX: width / videoW,
      scaleY: height / videoH,
    }
  }

  const width = containerW
  const height = containerW / videoAspect
  return {
    x: 0,
    y: (containerH - height) / 2,
    width,
    height,
    scaleX: width / videoW,
    scaleY: height / videoH,
  }
}

function clearCanvas() {
  const canvas = canvasRef.value
  const container = getContainer()
  if (!canvas || !container) return

  const rect = container.getBoundingClientRect()
  canvas.width = rect.width
  canvas.height = rect.height

  const ctx = canvas.getContext('2d')
  if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
}

function drawOverlay() {
  const canvas = canvasRef.value
  const container = getContainer()
  if (!canvas || !container || !props.active) return

  const rect = container.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return

  canvas.width = rect.width
  canvas.height = rect.height

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)
  if (!faces.length) return

  const videoRect = computeVideoRect(
    canvas.width,
    canvas.height,
    frameSize.width,
    frameSize.height,
  )

  for (const face of faces) {
    const box = face.box
    if (!box) continue

    const left = box.left ?? 0
    const top = box.top ?? 0
    const right = box.right ?? left
    const bottom = box.bottom ?? top
    if (right <= left || bottom <= top) continue

    const x = videoRect.x + left * videoRect.scaleX
    const y = videoRect.y + top * videoRect.scaleY
    const w = (right - left) * videoRect.scaleX
    const h = (bottom - top) * videoRect.scaleY

    const known = Boolean(face.known)
    const trusted = face.trusted !== false
    const color = !trusted ? '#ff9800' : (known ? '#00b400' : '#ff0000')
    const label = faceLabel(face)

    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.strokeRect(x, y, w, h)

    ctx.font = '600 14px system-ui, sans-serif'
    ctx.fillStyle = color
    ctx.fillText(label, x, Math.max(18, y - 6))
  }
}

function presenceMatchesStream(presence) {
  if (!presence?.stream_id) return false
  const legacyId = toZoneStreamId(props.streamId)
  return String(presence.stream_id) === String(legacyId)
}

function applyPresence(presence) {
  if (!presenceMatchesStream(presence)) {
    faces = []
    clearCanvas()
    return
  }

  faces = Array.isArray(presence.faces) ? presence.faces : []

  const size = presence.frame_size
  if (size?.width && size?.height) {
    frameSize = { width: size.width, height: size.height }
  }

  drawOverlay()
}

async function fetchPresence() {
  if (!props.active) return

  try {
    const data = await videoApi.status(props.streamId)
    applyPresence(data.presence)
  } catch {
    faces = []
    clearCanvas()
  }
}

function startPolling() {
  stopPolling()
  if (!props.active) return
  fetchPresence()
  pollTimer = window.setInterval(fetchPresence, POLL_MS)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

function setupResizeObserver() {
  const container = getContainer()
  if (!container || typeof ResizeObserver === 'undefined') return
  resizeObserver = new ResizeObserver(() => drawOverlay())
  resizeObserver.observe(container)
}

watch(
  () => [props.streamId, props.active],
  () => {
    faces = []
    frameSize = { ...DEFAULT_FRAME }
    clearCanvas()
    if (props.active) startPolling()
    else stopPolling()
  },
)

onMounted(() => {
  setupResizeObserver()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
  resizeObserver?.disconnect()
})
</script>

<template>
  <canvas
    ref="canvasRef"
    class="face-overlay"
    aria-hidden="true"
  />
</template>

<style scoped>
.face-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 2;
}
</style>

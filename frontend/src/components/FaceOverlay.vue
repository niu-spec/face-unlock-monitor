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
  presence: {
    type: Object,
    default: null,
  },
  managedExternally: {
    type: Boolean,
    default: false,
  },
})

const POLL_MS = 600
const DEFAULT_FRAME = { width: 1280, height: 720 }

const canvasRef = ref(null)
let pollTimer = null
let resizeObserver = null
let drawFrameId = null
let faces = []
let persons = []
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

function personLabel(person) {
  if (person.trusted === false) return '疑似欺骗'
  if (person.known && person.name) return person.name
  const confidence = Number(person.confidence)
  return Number.isFinite(confidence)
    ? `人物 ${Math.round(confidence * 100)}%`
    : '人物'
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
  const width = Math.max(1, Math.round(rect.width))
  const height = Math.max(1, Math.round(rect.height))
  if (canvas.width !== width) canvas.width = width
  if (canvas.height !== height) canvas.height = height

  const ctx = canvas.getContext('2d')
  if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
}

function drawOverlay() {
  const canvas = canvasRef.value
  const container = getContainer()
  if (!canvas || !container || !props.active) return

  const rect = container.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return

  const width = Math.max(1, Math.round(rect.width))
  const height = Math.max(1, Math.round(rect.height))
  // Assigning width/height clears and reallocates the entire backing store.
  // Only resize when layout actually changed, not on every polling response.
  if (canvas.width !== width) canvas.width = width
  if (canvas.height !== height) canvas.height = height

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)
  if (!faces.length && !persons.length) return

  const videoRect = computeVideoRect(
    canvas.width,
    canvas.height,
    frameSize.width,
    frameSize.height,
  )

  for (const person of persons) {
    const left = Number(person.x ?? 0)
    const top = Number(person.y ?? 0)
    const boxWidth = Number(person.w ?? 0)
    const boxHeight = Number(person.h ?? 0)
    if (boxWidth <= 0 || boxHeight <= 0) continue

    const x = videoRect.x + left * videoRect.scaleX
    const y = videoRect.y + top * videoRect.scaleY
    const w = boxWidth * videoRect.scaleX
    const h = boxHeight * videoRect.scaleY
    const color = person.trusted === false ? '#ff9800' : '#00e5ff'

    ctx.strokeStyle = color
    ctx.lineWidth = 3
    ctx.strokeRect(x, y, w, h)
    ctx.font = '600 14px system-ui, sans-serif'
    ctx.fillStyle = color
    ctx.fillText(personLabel(person), x, Math.max(18, y - 6))
  }

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

function scheduleDraw() {
  if (drawFrameId !== null) return
  drawFrameId = window.requestAnimationFrame(() => {
    drawFrameId = null
    drawOverlay()
  })
}

function presenceMatchesStream(presence) {
  if (!presence?.stream_id) return false
  const legacyId = toZoneStreamId(props.streamId)
  return String(presence.stream_id) === String(legacyId)
}

function applyPresence(presence) {
  if (!presenceMatchesStream(presence)) {
    faces = []
    persons = []
    clearCanvas()
    return
  }

  faces = Array.isArray(presence.faces) ? presence.faces : []
  persons = Array.isArray(presence.persons) ? presence.persons : []

  const size = presence.frame_size
  if (size?.width && size?.height) {
    frameSize = { width: size.width, height: size.height }
  }

  scheduleDraw()
}

async function fetchPresence() {
  if (!props.active || props.managedExternally) return

  try {
    const data = await videoApi.presence(props.streamId)
    applyPresence(data.presence)
  } catch {
    faces = []
    clearCanvas()
  }
}

function startPolling() {
  stopPolling()
  if (!props.active || props.managedExternally) return
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
  resizeObserver = new ResizeObserver(() => scheduleDraw())
  resizeObserver.observe(container)
}

watch(
  () => props.presence,
  (presence) => {
    if (presence) applyPresence(presence)
  },
  { deep: true },
)

watch(
  () => [props.streamId, props.active],
  () => {
    faces = []
    persons = []
    frameSize = { ...DEFAULT_FRAME }
    clearCanvas()
    if (props.active && !props.managedExternally) startPolling()
    else stopPolling()
  },
)

onMounted(() => {
  setupResizeObserver()
  if (props.presence) applyPresence(props.presence)
  if (!props.managedExternally) startPolling()
})

onUnmounted(() => {
  stopPolling()
  if (drawFrameId !== null) window.cancelAnimationFrame(drawFrameId)
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

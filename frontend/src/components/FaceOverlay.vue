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
  showRecognitionBoxes: {
    type: Boolean,
    default: true,
  },
  showAlertBoxes: {
    type: Boolean,
    default: true,
  },
})

const POLL_MS = 600
const DEFAULT_FRAME = { width: 1280, height: 720 }

const ALERT_LABELS = {
  FIRE: '火情',
  FALL: '摔倒',
  INTRUSION: '闯入',
  PROXIMITY: '过近',
  LOITER: '停留',
}

const ALERT_COLORS = {
  FIRE: '#ffa500',
  FALL: '#00ffff',
  INTRUSION: '#ff0000',
  PROXIMITY: '#ff8800',
  LOITER: '#e040fb',
}

const canvasRef = ref(null)
let pollTimer = null
let resizeObserver = null
let drawFrameId = null
let persons = []
let faceBoxes = []
let alertBoxes = []
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

function alertLabel(alert) {
  return ALERT_LABELS[alert.alert_type] || alert.alert_type || '异常'
}

function alertColor(alert) {
  return ALERT_COLORS[alert.alert_type] || '#ff5722'
}

function faceColor(face) {
  if (face.trusted === false) return '#ff9800'
  return face.known ? '#00b400' : '#ff0000'
}

function normalizeFaceBoxes(presence) {
  if (Array.isArray(presence.face_boxes) && presence.face_boxes.length) {
    return presence.face_boxes
  }

  const legacyFaces = Array.isArray(presence.faces) ? presence.faces : []
  return legacyFaces.flatMap((face, index) => {
    const box = face.box || {}
    const left = Number(box.left ?? 0)
    const top = Number(box.top ?? 0)
    const right = Number(box.right ?? left)
    const bottom = Number(box.bottom ?? top)
    const width = right - left
    const height = bottom - top
    if (width <= 0 || height <= 0) return []

    return [{
      x: left,
      y: top,
      w: width,
      h: height,
      track_id: Number(face.track_id ?? index),
      known: Boolean(face.known),
      name: face.name,
      role: face.role,
      trusted: face.trusted !== false,
    }]
  })
}

function normalizeAlertBoxes(presence) {
  return Array.isArray(presence.alert_boxes) ? presence.alert_boxes : []
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

function mapBoxToCanvas(videoRect, box) {
  const left = Number(box.x ?? 0)
  const top = Number(box.y ?? 0)
  const boxWidth = Number(box.w ?? 0)
  const boxHeight = Number(box.h ?? 0)
  if (boxWidth <= 0 || boxHeight <= 0) return null

  return {
    x: videoRect.x + left * videoRect.scaleX,
    y: videoRect.y + top * videoRect.scaleY,
    w: boxWidth * videoRect.scaleX,
    h: boxHeight * videoRect.scaleY,
  }
}

function drawRectBox(ctx, mapped, color, label, lineWidth = 2) {
  if (!mapped) return

  ctx.strokeStyle = color
  ctx.lineWidth = lineWidth
  ctx.strokeRect(mapped.x, mapped.y, mapped.w, mapped.h)
  ctx.font = '600 14px system-ui, sans-serif'
  ctx.fillStyle = color
  ctx.fillText(label, mapped.x, Math.max(18, mapped.y - 6))
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
  if (
    (!props.showAlertBoxes || !alertBoxes.length)
    && (!props.showRecognitionBoxes || (!persons.length && !faceBoxes.length))
  ) return

  const videoRect = computeVideoRect(
    canvas.width,
    canvas.height,
    frameSize.width,
    frameSize.height,
  )

  if (props.showRecognitionBoxes) {
    for (const person of persons) {
      const color = person.trusted === false ? '#ff9800' : '#00e5ff'
      drawRectBox(ctx, mapBoxToCanvas(videoRect, person), color, personLabel(person), 3)
    }
  }

  if (props.showAlertBoxes) {
    for (const alert of alertBoxes) {
      drawRectBox(
        ctx,
        mapBoxToCanvas(videoRect, alert),
        alertColor(alert),
        alertLabel(alert),
        3,
      )
    }
  }

  if (props.showRecognitionBoxes) {
    for (const face of faceBoxes) {
      drawRectBox(
        ctx,
        mapBoxToCanvas(videoRect, face),
        faceColor(face),
        faceLabel(face),
        2,
      )
    }
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
    persons = []
    faceBoxes = []
    alertBoxes = []
    clearCanvas()
    return
  }

  persons = Array.isArray(presence.persons) ? presence.persons : []
  faceBoxes = normalizeFaceBoxes(presence)
  alertBoxes = normalizeAlertBoxes(presence)

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
    persons = []
    faceBoxes = []
    alertBoxes = []
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
    persons = []
    faceBoxes = []
    alertBoxes = []
    frameSize = { ...DEFAULT_FRAME }
    clearCanvas()
    if (props.active && !props.managedExternally) startPolling()
    else stopPolling()
  },
)

watch(
  () => props.showRecognitionBoxes,
  () => scheduleDraw(),
)

watch(
  () => props.showAlertBoxes,
  () => scheduleDraw(),
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

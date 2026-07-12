<script setup>
import { computed, ref, watch } from 'vue'
import { fetchClipBlob, fetchSnapshotBlob } from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '事件回放' },
  description: { type: String, default: '' },
  timestamp: { type: String, default: '' },
  streamId: { type: String, default: '' },
  snapshotPath: { type: String, default: '' },
  clipPath: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const imageUrl = ref('')
const videoUrl = ref('')
const errorText = ref('')
const activeTab = ref('video')

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const hasClip = computed(() => Boolean(props.clipPath))
const hasSnapshot = computed(() => Boolean(props.snapshotPath))

function revokeUrls() {
  if (imageUrl.value) {
    URL.revokeObjectURL(imageUrl.value)
    imageUrl.value = ''
  }
  if (videoUrl.value) {
    URL.revokeObjectURL(videoUrl.value)
    videoUrl.value = ''
  }
}

async function loadClip() {
  if (!props.clipPath) return false
  try {
    const blob = await fetchClipBlob(props.clipPath)
    if (!blob || blob.size === 0) return false
    if (videoUrl.value) URL.revokeObjectURL(videoUrl.value)
    videoUrl.value = URL.createObjectURL(blob)
    return true
  } catch {
    return false
  }
}

async function loadSnapshot() {
  if (!props.snapshotPath) return false
  try {
    const blob = await fetchSnapshotBlob(props.snapshotPath)
    if (!blob || blob.size === 0) return false
    if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
    imageUrl.value = URL.createObjectURL(blob)
    return true
  } catch {
    return false
  }
}

async function loadReplay() {
  revokeUrls()
  errorText.value = ''
  loading.value = true
  try {
    const clipOk = await loadClip()
    const snapshotOk = await loadSnapshot()
    if (clipOk) {
      activeTab.value = 'video'
    } else if (snapshotOk) {
      activeTab.value = 'snapshot'
    }
    if (!clipOk && !snapshotOk) {
      errorText.value = props.clipPath
        ? '短视频正在生成或加载失败，请稍后刷新列表再试'
        : '该记录暂无回放素材'
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.snapshotPath, props.clipPath],
  ([open]) => {
    if (open) loadReplay()
    else revokeUrls()
  },
)
</script>

<template>
  <el-dialog v-model="visible" :title="title" width="760px" destroy-on-close @closed="revokeUrls">
    <el-tabs v-if="hasClip && hasSnapshot" v-model="activeTab" class="replay-tabs">
      <el-tab-pane label="视频回放" name="video" />
      <el-tab-pane label="截图" name="snapshot" />
    </el-tabs>

    <div v-loading="loading" class="replay-body">
      <video
        v-if="videoUrl && (activeTab === 'video' || (!hasSnapshot && hasClip))"
        :src="videoUrl"
        class="replay-video"
        controls
        playsinline
        autoplay
      />
      <img
        v-else-if="imageUrl && (activeTab === 'snapshot' || !hasClip)"
        :src="imageUrl"
        alt="事件回放截图"
        class="replay-image"
      />
      <el-empty v-else-if="errorText" :description="errorText" />
    </div>

    <p v-if="hasClip && !videoUrl && !loading" class="replay-hint">
      告警短视频约 10 秒后生成，请关闭后重新打开回放，或等待列表自动刷新。
    </p>

    <div class="replay-meta">
      <p v-if="timestamp"><strong>时间：</strong>{{ timestamp }}</p>
      <p v-if="streamId"><strong>摄像头：</strong>{{ streamId }}</p>
      <p v-if="description"><strong>描述：</strong>{{ description }}</p>
    </div>
  </el-dialog>
</template>

<style scoped>
.replay-tabs {
  margin-bottom: 8px;
}

.replay-body {
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.replay-video,
.replay-image {
  width: 100%;
  max-height: 420px;
  object-fit: contain;
}

.replay-hint {
  margin: 8px 0 0;
  color: #909399;
  font-size: 12px;
}

.replay-meta {
  margin-top: 12px;
  color: #606266;
  font-size: 13px;
  line-height: 1.7;
}

.replay-meta p {
  margin: 0;
}
</style>

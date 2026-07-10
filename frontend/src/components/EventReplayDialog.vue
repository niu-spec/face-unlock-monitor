<script setup>
import { computed, ref, watch } from 'vue'
import { fetchSnapshotBlob } from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '事件回放' },
  description: { type: String, default: '' },
  timestamp: { type: String, default: '' },
  streamId: { type: String, default: '' },
  snapshotPath: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const imageUrl = ref('')
const errorText = ref('')

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

function revokeImageUrl() {
  if (imageUrl.value) {
    URL.revokeObjectURL(imageUrl.value)
    imageUrl.value = ''
  }
}

async function loadSnapshot() {
  revokeImageUrl()
  errorText.value = ''
  if (!props.snapshotPath) {
    errorText.value = '该记录暂无截图回放'
    return
  }

  loading.value = true
  try {
    const blob = await fetchSnapshotBlob(props.snapshotPath)
    if (!blob || blob.size === 0) {
      errorText.value = '截图加载失败'
      return
    }
    imageUrl.value = URL.createObjectURL(blob)
  } catch {
    errorText.value = '截图加载失败或已过期'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.snapshotPath],
  ([open]) => {
    if (open) loadSnapshot()
    else revokeImageUrl()
  },
)
</script>

<template>
  <el-dialog v-model="visible" :title="title" width="720px" destroy-on-close @closed="revokeImageUrl">
    <div v-loading="loading" class="replay-body">
      <img v-if="imageUrl" :src="imageUrl" alt="事件回放截图" class="replay-image" />
      <el-empty v-else-if="errorText" :description="errorText" />
    </div>
    <div class="replay-meta">
      <p v-if="timestamp"><strong>时间：</strong>{{ timestamp }}</p>
      <p v-if="streamId"><strong>摄像头：</strong>{{ streamId }}</p>
      <p v-if="description"><strong>描述：</strong>{{ description }}</p>
    </div>
  </el-dialog>
</template>

<style scoped>
.replay-body {
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.replay-image {
  width: 100%;
  max-height: 420px;
  object-fit: contain;
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

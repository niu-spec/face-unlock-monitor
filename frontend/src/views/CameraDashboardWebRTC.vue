<script setup>
import { reactive } from 'vue'

const cameras = [
  {
    id: 'camera_1',
    name: '摄像头 1',
    position: '低延迟测试通道',
    webrtcUrl: 'http://152.136.29.158:18889/stream/99/',
    mjpegUrl: 'http://152.136.29.158/video_feed/1',
  },
  {
    id: 'camera_2',
    name: '摄像头 2',
    position: '兼容备用通道',
    webrtcUrl: 'http://152.136.29.158:18889/stream/99/',
    mjpegUrl: 'http://152.136.29.158/video_feed/2',
  },
]

const activePreview = reactive(
  cameras.reduce((result, camera) => {
    result[camera.id] = 'webrtc'
    return result
  }, {}),
)

function openPreview(url) {
  window.open(url, '_blank', 'noopener,noreferrer')
}
</script>

<template>
  <div class="camera-dashboard">
    <el-alert
      class="mode-note"
      title="WebRTC 用于低延迟预览；MJPEG 用于兼容备用。"
      type="info"
      show-icon
      :closable="false"
    />

    <el-row :gutter="16">
      <el-col v-for="camera in cameras" :key="camera.id" :xs="24" :lg="12">
        <el-card class="camera-card" shadow="never">
          <template #header>
            <div class="card-header">
              <div>
                <div class="camera-name">{{ camera.name }}</div>
                <div class="camera-position">{{ camera.position }}</div>
              </div>
              <el-tag type="success" effect="plain">在线预览</el-tag>
            </div>
          </template>

          <el-segmented
            v-model="activePreview[camera.id]"
            class="preview-switch"
            :options="[
              { label: '低延迟预览 WebRTC', value: 'webrtc' },
              { label: '兼容预览 MJPEG', value: 'mjpeg' },
            ]"
          />

          <div class="preview-frame">
            <iframe
              v-if="activePreview[camera.id] === 'webrtc'"
              :src="camera.webrtcUrl"
              title="低延迟 WebRTC 预览"
              allow="autoplay; fullscreen; microphone; camera"
            />
            <img
              v-else
              :src="camera.mjpegUrl"
              :alt="`${camera.name} MJPEG 兼容预览`"
            />
          </div>

          <div class="preview-actions">
            <el-button type="primary" plain @click="openPreview(camera.webrtcUrl)">
              低延迟预览 WebRTC
            </el-button>
            <el-button plain @click="openPreview(camera.mjpegUrl)">
              兼容预览 MJPEG
            </el-button>
          </div>

          <div class="stream-links">
            <div>
              <span>WebRTC</span>
              <a :href="camera.webrtcUrl" target="_blank" rel="noopener noreferrer">
                {{ camera.webrtcUrl }}
              </a>
            </div>
            <div>
              <span>MJPEG</span>
              <a :href="camera.mjpegUrl" target="_blank" rel="noopener noreferrer">
                {{ camera.mjpegUrl }}
              </a>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.camera-dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mode-note {
  border-radius: 8px;
}

.camera-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.camera-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.camera-position {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}

.preview-switch {
  width: 100%;
  margin-bottom: 12px;
}

.preview-frame {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 360px;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.preview-frame iframe,
.preview-frame img {
  width: 100%;
  height: 360px;
  border: 0;
  object-fit: contain;
}

.preview-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.preview-actions .el-button + .el-button {
  margin-left: 0;
}

.stream-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  font-size: 13px;
}

.stream-links div {
  display: flex;
  gap: 8px;
  min-width: 0;
}

.stream-links span {
  flex: 0 0 58px;
  color: #606266;
  font-weight: 600;
}

.stream-links a {
  min-width: 0;
  color: var(--el-color-primary);
  overflow-wrap: anywhere;
  text-decoration: none;
}

@media (max-width: 768px) {
  .preview-frame {
    min-height: 240px;
  }

  .preview-frame iframe,
  .preview-frame img {
    height: 240px;
  }
}
</style>

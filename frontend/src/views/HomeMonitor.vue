<script setup>
import { ref } from 'vue'
import PersonStats from '@/components/PersonStats.vue'
import { videoFeedUrl } from '@/api'
import { CAMERA_STREAMS, DEFAULT_STREAM_ID } from '@/constants/streams'

const activeStream = ref(DEFAULT_STREAM_ID)
const videoError = ref(false)

function onVideoError() {
  videoError.value = true
}

function onVideoLoad() {
  videoError.value = false
}
</script>

<template>
  <div class="monitor-page">
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>实时画面</span>
              <el-radio-group v-model="activeStream" size="small">
                <el-radio-button v-for="item in CAMERA_STREAMS" :key="item.id" :value="item.id">
                  {{ item.label }}
                </el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div class="video-box">
            <img
              :key="activeStream"
              :src="videoFeedUrl(activeStream)"
              alt="实时画面"
              @error="onVideoError"
              @load="onVideoLoad"
            />
            <div v-if="videoError" class="video-fallback">
              视频流未就绪（推流码 {{ activeStream }}）<br />
              请确认 MediaMTX 与 OBS 已启动
            </div>
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

.video-box img {
  width: 100%;
  max-height: 480px;
  object-fit: contain;
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
</style>

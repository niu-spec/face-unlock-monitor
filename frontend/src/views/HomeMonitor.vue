<script setup>
import { ref } from 'vue'
import PersonStats from '@/components/PersonStats.vue'
import { videoFeedUrl } from '@/api'

const streams = [
  { id: '1', label: '摄像头 1' },
  { id: '2', label: '摄像头 2' },
]

const activeStream = ref('1')
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
                <el-radio-button v-for="item in streams" :key="item.id" :value="item.id">
                  {{ item.label }}
                </el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div class="video-box">
            <img :src="videoFeedUrl(activeStream)" alt="实时画面" />
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
</style>

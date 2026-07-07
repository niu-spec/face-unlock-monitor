<script setup>
import { ref } from 'vue'

const filterType = ref('')
const alerts = ref([])

const typeOptions = [
  { label: '全部', value: '' },
  { label: '陌生人', value: 'FACE_UNKNOWN' },
  { label: '区域闯入', value: 'ZONE_INTRUSION' },
  { label: '积水', value: 'FLOOD' },
  { label: '着火', value: 'FIRE' },
  { label: '摔倒', value: 'FALL' },
]
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="header">
        <span>告警中心</span>
        <el-select v-model="filterType" placeholder="按类型筛选" style="width: 180px">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </div>
    </template>

    <el-empty description="暂无告警，联调 GET /api/alerts 后展示" />
    <el-table v-if="alerts.length" :data="alerts" stripe>
      <el-table-column prop="type" label="类型" width="140" />
      <el-table-column prop="message" label="描述" />
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="操作" width="120">
        <template #default>
          <el-button link type="primary">处置</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>

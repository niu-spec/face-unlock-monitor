<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { alertApi } from '@/api'

const filterType = ref('')
const alerts = ref([])
const loading = ref(false)

const typeOptions = [
  { label: '全部', value: '' },
  { label: '陌生人', value: 'FACE_UNKNOWN' },
  { label: '区域闯入', value: 'INTRUSION' },
  { label: '距离过近', value: 'PROXIMITY' },
  { label: '异常停留', value: 'LOITER' },
  { label: '尾随进入', value: 'TAILGATE' },
  { label: '火情', value: 'FIRE' },
  { label: '积水', value: 'WATER' },
  { label: '人员摔倒', value: 'FALL' },
]

async function loadAlerts() {
  loading.value = true
  try {
    const params = filterType.value ? { type: filterType.value } : {}
    const data = await alertApi.list(params)
    alerts.value = data.results || data
  } catch { alerts.value = [] }
  finally { loading.value = false }
}

async function handleAlert(alert) {
  try {
    await alertApi.handle(alert.id)
    ElMessage.success('已处置')
    loadAlerts()
  } catch { /* ignore */ }
}

onMounted(loadAlerts)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="header">
        <span>告警中心</span>
        <el-select v-model="filterType" placeholder="按类型筛选" style="width: 180px" @change="loadAlerts">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </div>
    </template>

    <el-table v-if="alerts.length" :data="alerts" stripe v-loading="loading">
      <el-table-column label="类型" width="120">
        <template #default="{ row }">{{ row.type_display || row.type }}</template>
      </el-table-column>
      <el-table-column prop="description" label="描述" />
      <el-table-column label="等级" width="80">
        <template #default="{ row }">
          <el-tag :type="row.level === 'HIGH' ? 'danger' : row.level === 'MEDIUM' ? 'warning' : 'info'" size="small">
            {{ row.level_display || row.level }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" link type="primary" @click="handleAlert(row)">处置</el-button>
          <el-tag v-else size="small" type="success">已处理</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="暂无告警" />
  </el-card>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>

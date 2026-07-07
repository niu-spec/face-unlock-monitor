<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { zoneApi } from '@/api'

const zones = ref([])
const loading = ref(false)

const form = reactive({
  name: '',
  stream_id: 'living_room',
  forbidden_roles: [],
  safe_distance: 50,
  dwell_time: 5,
})

const roleOptions = [
  { label: '小孩', value: 'child' },
  { label: '成人', value: 'adult' },
  { label: '老人', value: 'elder' },
  { label: '访客', value: 'guest' },
]

async function loadZones() {
  loading.value = true
  try {
    const data = await zoneApi.list()
    zones.value = data.results || data
  } catch { zones.value = [] }
  finally { loading.value = false }
}

async function onSave() {
  if (!form.name.trim()) { ElMessage.warning('请输入区域名称'); return }

  try {
    await zoneApi.create({
      name: form.name.trim(),
      stream_id: form.stream_id,
      points_json: [[100, 100], [400, 100], [400, 350], [100, 350]],
      forbidden_roles: form.forbidden_roles,
      safe_distance: form.safe_distance,
      dwell_time: form.dwell_time,
    })
    ElMessage.success('区域已保存')
    form.name = ''
    form.forbidden_roles = []
    loadZones()
  } catch { /* handled by interceptor */ }
}

async function removeZone(zone) {
  try {
    await zoneApi.remove(zone.id)
    ElMessage.success('已删除')
    loadZones()
  } catch { /* ignore */ }
}

onMounted(loadZones)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="header">
        <span>危险区域配置</span>
      </div>
    </template>

    <!-- 新增区域表单 -->
    <el-form :model="form" label-width="100px" style="max-width: 600px; margin-bottom: 24px">
      <el-form-item label="区域名称">
        <el-input v-model="form.name" placeholder="如：厨房禁区" />
      </el-form-item>
      <el-form-item label="摄像头">
        <el-select v-model="form.stream_id">
          <el-option label="客厅" value="living_room" />
          <el-option label="厨房" value="kitchen" />
        </el-select>
      </el-form-item>
      <el-form-item label="禁止角色">
        <el-checkbox-group v-model="form.forbidden_roles">
          <el-checkbox v-for="r in roleOptions" :key="r.value" :label="r.value" :value="r.value">
            {{ r.label }}
          </el-checkbox>
        </el-checkbox-group>
        <div style="color: #999; font-size: 12px; margin-top: 4px">
          已选：{{ form.forbidden_roles.length ? form.forbidden_roles.map(r => roleOptions.find(o => o.value === r)?.label).join('、') : '无' }}
        </div>
      </el-form-item>
      <el-form-item label="安全距离(px)">
        <el-input-number v-model="form.safe_distance" :min="10" :max="500" />
      </el-form-item>
      <el-form-item label="停留阈值(秒)">
        <el-input-number v-model="form.dwell_time" :min="1" :max="120" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSave">保存区域</el-button>
      </el-form-item>
    </el-form>

    <!-- 已有区域列表 -->
    <el-divider />
    <div v-if="zones.length" v-loading="loading">
      <el-table :data="zones" stripe>
        <el-table-column prop="name" label="区域名称" />
        <el-table-column prop="stream_id_display" label="摄像头" width="100" />
        <el-table-column label="禁止角色" width="180">
          <template #default="{ row }">
            <el-tag v-for="r in row.forbidden_roles" :key="r" size="small" style="margin-right: 4px">
              {{ roleOptions.find(o => o.value === r)?.label || r }}
            </el-tag>
            <span v-if="!row.forbidden_roles?.length" style="color: #999">无</span>
          </template>
        </el-table-column>
        <el-table-column prop="safe_distance" label="安全距离" width="100" />
        <el-table-column prop="dwell_time" label="停留阈值" width="100" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="danger" @click="removeZone(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-empty v-else description="暂无区域配置，请创建" />

    <!-- Canvas 画框占位 -->
    <div class="canvas-placeholder">
      Canvas 画框区域（待接入摄像头画面与多边形编辑）
    </div>
  </el-card>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.canvas-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  border: 2px dashed var(--el-border-color);
  border-radius: 8px;
  color: var(--el-text-color-secondary);
  background: #fff;
  margin-top: 16px;
}
</style>

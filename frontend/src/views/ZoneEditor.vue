<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const zoneName = ref('厨房')
const forbiddenRole = ref('child')

function onSave() {
  ElMessage.info('危险区域保存接口联调中（CRUD /api/zones）')
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="header">
        <span>危险区域画框</span>
        <el-button type="primary" @click="onSave">保存区域</el-button>
      </div>
    </template>

    <el-form inline>
      <el-form-item label="区域名称">
        <el-input v-model="zoneName" />
      </el-form-item>
      <el-form-item label="禁止角色">
        <el-select v-model="forbiddenRole">
          <el-option label="小孩" value="child" />
          <el-option label="成人" value="adult" />
        </el-select>
      </el-form-item>
    </el-form>

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
  min-height: 420px;
  border: 2px dashed var(--el-border-color);
  border-radius: 8px;
  color: var(--el-text-color-secondary);
  background: #fff;
}
</style>

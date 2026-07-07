<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

const form = reactive({
  name: '',
  role: 'adult',
  image: null,
})

const previewUrl = ref('')

function onFileChange(file) {
  form.image = file.raw
  previewUrl.value = URL.createObjectURL(file.raw)
}

function onSubmit() {
  ElMessage.info('家人注册接口联调中（POST /api/face/register）')
}
</script>

<template>
  <el-card shadow="never">
    <template #header>家庭成员人脸录入</template>
    <el-form :model="form" label-width="88px" style="max-width: 560px">
      <el-form-item label="姓名">
        <el-input v-model="form.name" placeholder="如：爸爸" />
      </el-form-item>
      <el-form-item label="角色">
        <el-radio-group v-model="form.role">
          <el-radio value="adult">成人</el-radio>
          <el-radio value="child">小孩</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="照片">
        <el-upload drag :auto-upload="false" :show-file-list="false" accept="image/*" @change="onFileChange">
          <el-icon><UploadFilled /></el-icon>
          <div>点击或拖拽上传人脸照片</div>
        </el-upload>
        <img v-if="previewUrl" :src="previewUrl" class="preview" alt="预览" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSubmit">注册家人</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
.preview {
  display: block;
  margin-top: 12px;
  width: 160px;
  border-radius: 8px;
}
</style>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { memberApi } from '@/api'

const form = reactive({
  name: '',
  role: 'adult',
  student_id: '',
})

const previewUrl = ref('')
const photoFile = ref(null)
const submitting = ref(false)

function onFileChange(file) {
  photoFile.value = file.raw
  previewUrl.value = URL.createObjectURL(file.raw)
}

async function onSubmit() {
  if (!form.name.trim()) { ElMessage.warning('请输入姓名'); return }

  submitting.value = true
  try {
    const data = { name: form.name.trim(), role: form.role, student_id: form.student_id }
    // 如果后续需要上传人脸照片，可以在这里转 base64
    if (photoFile.value) {
      // 预留：将照片转 base64 传给 face_encoding
      // const reader = new FileReader()
      // data.image_base64 = await new Promise((resolve) => {
      //   reader.onload = (e) => resolve(e.target.result.split(',')[1])
      //   reader.readAsDataURL(photoFile.value)
      // })
    }
    await memberApi.create(data)
    ElMessage.success('家庭成员已录入')
    form.name = ''
    form.student_id = ''
    photoFile.value = null
    previewUrl.value = ''
  } catch { /* error handled by interceptor */ }
  finally { submitting.value = false }
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
          <el-radio value="elder">老人</el-radio>
          <el-radio value="guest">访客</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="学号/工号">
        <el-input v-model="form.student_id" placeholder="可选" />
      </el-form-item>
      <el-form-item label="人脸照片">
        <el-upload
          drag
          :auto-upload="false"
          :show-file-list="false"
          accept="image/*"
          @change="onFileChange"
        >
          <el-icon :size="40"><UploadFilled /></el-icon>
          <div class="upload-text">点击或拖拽上传人脸照片</div>
        </el-upload>
        <img v-if="previewUrl" :src="previewUrl" class="preview" alt="预览" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSubmit" :loading="submitting">录入成员</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
.upload-text {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.preview {
  display: block;
  margin-top: 12px;
  width: 200px;
  height: 200px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--el-border-color);
}
</style>

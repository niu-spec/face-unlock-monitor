<script setup>
import { reactive, ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import FaceCapture from '@/components/FaceCapture.vue'
import { memberApi, householdApi } from '@/api'
import request from '@/api/request'

const activeHouseholdName = ref('')
const activeHouseholdId = ref(localStorage.getItem('activeHouseholdId') || '')

const form = reactive({ name: '', identity: '', role: 'adult' })
const inputMode = ref('camera')
const previewUrl = ref('')
const photoFile = ref(null)
const photoFiles = ref([])
const submitting = ref(false)
const submitHint = ref('')
const members = ref([])
const captureRef = ref(null)

let previewObjectUrl = ''

function setPreview(file, url, files = [file]) {
  if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl)
  photoFile.value = file
  photoFiles.value = files.filter(Boolean)
  previewUrl.value = url
  previewObjectUrl = url
}

function onFileChange(file) {
  setPreview(file.raw, URL.createObjectURL(file.raw))
}

function onCameraCapture({ file, previewUrl: url }) {
  setPreview(file, url)
}

function onCameraCaptureSequence({ files, previewUrl: url }) {
  const selected = Array.isArray(files) ? files.filter(Boolean) : []
  setPreview(selected[selected.length - 1], url, selected)
}

watch(inputMode, (mode) => {
  if (mode === 'upload') {
    captureRef.value?.stopCamera?.()
  } else {
    captureRef.value?.startCamera?.()
  }
})

async function loadHouseholdInfo() {
  if (!activeHouseholdId.value) return
  try {
    const data = await householdApi.list()
    const list = data.results || data
    const h = list.find((item) => item.id === Number(activeHouseholdId.value))
    if (h) activeHouseholdName.value = h.name
  } catch (err) {
    console.error('加载家庭信息失败:', err)
  }
}

async function loadMembers() {
  if (!activeHouseholdId.value) return
  try {
    const data = await memberApi.list()
    members.value = data.results || data
  } catch (err) {
    ElMessage.error('加载家庭成员列表失败')
    console.error('加载家庭成员失败:', err)
  }
}

function clearPhoto() {
  if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl)
  previewObjectUrl = ''
  photoFile.value = null
  photoFiles.value = []
  previewUrl.value = ''
}

async function onSubmit() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入姓名')
    return
  }
  if (!activeHouseholdId.value) {
    ElMessage.warning('请先在家庭管理中切换到当前家庭')
    return
  }
  if (!photoFile.value) {
    ElMessage.warning(
      inputMode.value === 'camera'
        ? '请先点击「截取当前画面」'
        : '请上传一张清晰的单人人脸照片',
    )
    return
  }

  submitting.value = true
  submitHint.value = inputMode.value === 'camera' && photoFiles.value.length >= 3 ? '活体检测中...' : ''
  const data = new FormData()
  data.append('name', form.name.trim())
  data.append('identity', form.identity.trim())
  data.append('role', form.role)
  data.append('household_id', activeHouseholdId.value)
  if (inputMode.value === 'camera' && photoFiles.value.length >= 3) {
    photoFiles.value.forEach((file) => data.append('images', file))
  } else {
    data.append('image', photoFile.value)
  }

  try {
    await request.post('/api/face/register/', data, { silent: true })
    ElMessage.success('家庭成员与人脸特征已录入')
    form.name = ''
    form.identity = ''
    clearPhoto()
    loadMembers()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.response?.data?.detail || ''
    if (typeof msg === 'string' && (msg.includes('face_recognition') || msg.includes('dlib'))) {
      try {
        await memberApi.create({
          name: form.name.trim(),
          identity: form.identity.trim(),
          role: form.role,
          household_id: Number(activeHouseholdId.value),
        })
        ElMessage.warning('成员已保存；本地未安装人脸识别库，人脸特征需在服务器环境补录')
        form.name = ''
        form.identity = ''
        clearPhoto()
        loadMembers()
      } catch {
        /* interceptor shows error */
      }
    }
  } finally {
    submitting.value = false
    submitHint.value = ''
  }
}

async function removeMember(member) {
  try {
    await memberApi.remove(member.id)
    ElMessage.success('已删除')
    loadMembers()
  } catch {
    /* ignore */
  }
}

onMounted(() => {
  loadHouseholdInfo()
  loadMembers()
})
</script>

<template>
  <div class="family-page">
    <el-alert
      v-if="!activeHouseholdId"
      title="请先在「家庭管理」中创建或切换到一个家庭"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <el-card shadow="never">
      <template #header>
        <span>家庭成员录入</span>
        <el-tag v-if="activeHouseholdName" type="success" style="margin-left: 12px">
          {{ activeHouseholdName }}
        </el-tag>
      </template>
      <el-form :model="form" label-width="88px" style="max-width: 640px">
        <el-form-item label="姓名">
          <el-input v-model="form.name" placeholder="如：张三" />
        </el-form-item>
        <el-form-item label="身份">
          <el-input v-model="form.identity" placeholder="如：爸爸、妈妈" />
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio value="adult">成人</el-radio>
            <el-radio value="child">小孩</el-radio>
            <el-radio value="elder">老人</el-radio>
            <el-radio value="guest">访客</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="录入方式">
          <el-radio-group v-model="inputMode">
            <el-radio value="camera">摄像头</el-radio>
            <el-radio value="upload">上传照片</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="人脸采集">
          <FaceCapture
            v-if="inputMode === 'camera'"
            ref="captureRef"
            @capture="onCameraCapture"
            @capture-sequence="onCameraCaptureSequence"
          />
          <template v-else>
            <el-upload drag :auto-upload="false" :show-file-list="false" accept="image/*" @change="onFileChange">
              <el-icon :size="40"><UploadFilled /></el-icon>
              <div class="upload-text">点击或拖拽上传人脸照片</div>
            </el-upload>
          </template>
          <div v-if="previewUrl" class="preview-wrap">
            <img :src="previewUrl" class="preview" alt="待录入预览" />
            <el-button link type="danger" @click="clearPhoto">清除重拍</el-button>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="onSubmit">
            {{ submitHint || '录入成员' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="activeHouseholdId" shadow="never" style="margin-top: 16px">
      <template #header>家庭成员列表</template>
      <el-table v-if="members.length" :data="members" stripe>
        <el-table-column prop="name" label="姓名" />
        <el-table-column label="身份" width="100">
          <template #default="{ row }">
            {{ row.identity || '—' }}
          </template>
        </el-table-column>
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.role_display || row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="人脸" width="80">
          <template #default="{ row }">
            <el-tag :type="row.face_encoding ? 'success' : 'info'" size="small">
              {{ row.face_encoding ? '已录入' : '未录入' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="录入时间" width="180" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="danger" @click="removeMember(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无家庭成员，请录入" />
    </el-card>
  </div>
</template>

<style scoped>
.family-page {
  max-width: 760px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .family-page {
    max-width: 100%;
  }

  .family-page :deep(.el-form-item__label) {
    width: 100% !important;
    justify-content: flex-start;
  }

  .family-page :deep(.el-form-item__content) {
    margin-left: 0 !important;
  }
}

.upload-text {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.preview-wrap {
  margin-top: 12px;
}

.preview {
  display: block;
  width: 200px;
  height: 200px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--el-border-color);
}
</style>

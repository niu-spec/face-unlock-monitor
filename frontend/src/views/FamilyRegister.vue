<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { memberApi, householdApi, faceApi } from '@/api'

const activeHouseholdName = ref('')
const activeHouseholdId = ref(localStorage.getItem('activeHouseholdId') || '')

const form = reactive({ name: '', role: 'adult' })
const previewUrl = ref('')
const photoFile = ref(null)
const submitting = ref(false)
const members = ref([])

async function loadHouseholdInfo() {
  if (!activeHouseholdId.value) return
  try {
    const data = await householdApi.list()
    const list = data.results || data
    const h = list.find(h => h.id === Number(activeHouseholdId.value))
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

function onFileChange(file) {
  photoFile.value = file.raw
  previewUrl.value = URL.createObjectURL(file.raw)
}

async function onSubmit() {
  if (!form.name.trim()) { ElMessage.warning('请输入姓名'); return }
  if (!activeHouseholdId.value) { ElMessage.warning('请先在家庭管理中切换到当前家庭'); return }
  if (!photoFile.value) { ElMessage.warning('请上传一张清晰的单人人脸照片'); return }

  submitting.value = true
  try {
    const data = new FormData()
    data.append('name', form.name.trim())
    data.append('role', form.role)
    data.append('image', photoFile.value)
    await faceApi.register(data)
    ElMessage.success('家庭成员与人脸特征已录入')
    form.name = ''
    photoFile.value = null
    previewUrl.value = ''
    loadMembers()
  } catch { /* ignore */ }
  finally { submitting.value = false }
}

async function removeMember(member) {
  try {
    await memberApi.remove(member.id)
    ElMessage.success('已删除')
    loadMembers()
  } catch { /* ignore */ }
}

onMounted(() => { loadHouseholdInfo(); loadMembers() })
</script>

<template>
  <div class="family-page">
    <!-- 当前家庭提示 -->
    <el-alert
      v-if="!activeHouseholdId"
      title="请先在「家庭管理」中创建或切换到一个家庭"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <!-- 录入表单 -->
    <el-card shadow="never">
      <template #header>
        <span>家庭成员录入</span>
        <el-tag v-if="activeHouseholdName" type="success" style="margin-left: 12px">
          {{ activeHouseholdName }}
        </el-tag>
      </template>
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
        <el-form-item label="人脸照片">
          <el-upload drag :auto-upload="false" :show-file-list="false" accept="image/*" @change="onFileChange">
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

    <!-- 已有成员 -->
    <el-card v-if="activeHouseholdId" shadow="never" style="margin-top: 16px">
      <template #header>家庭成员列表</template>
      <el-table v-if="members.length" :data="members" stripe>
        <el-table-column prop="name" label="姓名" />
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
.family-page { max-width: 700px; margin: 0 auto; }

.upload-text { margin-top: 8px; color: var(--el-text-color-secondary); font-size: 13px; }

.preview { display: block; margin-top: 12px; width: 200px; height: 200px; object-fit: cover; border-radius: 8px; border: 1px solid var(--el-border-color); }
</style>

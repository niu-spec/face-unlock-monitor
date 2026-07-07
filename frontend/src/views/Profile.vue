<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'

const loading = ref(false)
const form = reactive({
  phone: '',
  nickname: '',
})

async function loadProfile() {
  try {
    const data = await authApi.getMe()
    form.phone = data.phone || ''
    form.nickname = data.nickname || ''
    // 更新本地缓存
    localStorage.setItem('user', JSON.stringify({ id: data.id, phone: data.phone, nickname: data.nickname }))
  } catch { /* ignore */ }
}

async function saveProfile() {
  if (!form.nickname.trim()) { ElMessage.warning('请输入昵称'); return }
  loading.value = true
  try {
    await authApi.updateProfile({
      nickname: form.nickname.trim(),
      phone: form.phone,
    })
    ElMessage.success('保存成功')
    localStorage.setItem('user', JSON.stringify({ phone: form.phone, nickname: form.nickname.trim() }))
    // 刷新页面以更新顶栏显示
    window.location.reload()
  } catch { /* ignore */ }
  finally { loading.value = false }
}

onMounted(loadProfile)
</script>

<template>
  <div class="profile-page">
    <el-card shadow="never">
      <template #header>个人信息</template>
      <el-form :model="form" label-width="80px" style="max-width: 480px">
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="手机号" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="设置一个昵称" maxlength="32" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="saveProfile">保存修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 600px;
  margin: 0 auto;
}
</style>

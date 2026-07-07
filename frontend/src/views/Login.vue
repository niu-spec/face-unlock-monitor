<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'

const router = useRouter()
const loading = ref(false)
const form = reactive({
  username: 'admin',
  password: 'admin123',
})

async function onSubmit() {
  loading.value = true
  try {
    const data = await authApi.login(form)
    const token = data?.access || data?.token
    if (token) {
      localStorage.setItem('token', token)
    }
    ElMessage.success('登录成功')
    router.push('/monitor')
  } catch {
    ElMessage.warning('后端未就绪，已进入演示模式')
    router.push('/monitor')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <template #header>
        <div class="title">居家智能摄像头监控</div>
      </template>
      <el-form :model="form" label-width="72px" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #e8f3ff 0%, #f5f7fa 100%);
}

.login-card {
  width: 420px;
}

.title {
  text-align: center;
  font-size: 18px;
  font-weight: 600;
}
</style>

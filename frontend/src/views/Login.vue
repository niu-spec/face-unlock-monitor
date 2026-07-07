<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const form = reactive({
  phone: '',
  password: '',
})

async function onSubmit() {
  if (!form.phone || form.phone.length !== 11) {
    ElMessage.warning('请输入有效的手机号')
    return
  }
  if (!form.password || form.password.length < 6) {
    ElMessage.warning('密码至少6位')
    return
  }

  loading.value = true
  try {
    // 先清除所有旧登录数据，避免残留旧账号信息
    localStorage.removeItem('token')
    localStorage.removeItem('refresh')
    localStorage.removeItem('activeHouseholdId')
    localStorage.removeItem('user')
    localStorage.removeItem('households')

    const data = await authApi.login(form)
    localStorage.setItem('token', data.access)
    localStorage.setItem('refresh', data.refresh)
    if (data.user) {
      localStorage.setItem('user', JSON.stringify(data.user))
    }
    // 获取用户家庭列表，设置默认活跃家庭
    try {
      const me = await authApi.getMe()
      if (me.households && me.households.length > 0) {
        localStorage.setItem('activeHouseholdId', me.households[0].id)
        localStorage.setItem('households', JSON.stringify(me.households))
      }
    } catch { /* 忽略 */ }
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/monitor'
    router.push(redirect)
  } catch {
    ElMessage.error('手机号或密码错误')
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
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="请输入手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <div style="text-align: center">
        <router-link to="/register">没有账号？立即注册</router-link>
      </div>
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

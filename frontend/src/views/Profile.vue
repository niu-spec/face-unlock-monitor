<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'

const currentPhone = ref('')
const changing = ref(false)
const smsCountdown = ref(0)

const form = reactive({
  phone: '',
  smsCode: '',
})

async function loadProfile() {
  try {
    const data = await authApi.getMe()
    currentPhone.value = data.phone || ''
    localStorage.setItem('user', JSON.stringify({ phone: data.phone }))
  } catch { /* ignore */ }
}

async function sendSms() {
  if (!/^1[3-9]\d{9}$/.test(form.phone)) { ElMessage.warning('请输入有效的新手机号'); return }
  try {
    const data = await authApi.sendSms({ phone: form.phone })
    if (data.dev_code) {
      ElMessage.success(`验证码已发送（开发模式：${data.dev_code}）`)
    } else {
      ElMessage.success('验证码已发送')
    }
    smsCountdown.value = 60
    const timer = setInterval(() => {
      smsCountdown.value--
      if (smsCountdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch { /* ignore */ }
}

async function changePhone() {
  if (!form.smsCode) { ElMessage.warning('请输入验证码'); return }

  try {
    await authApi.changePhone({ phone: form.phone, sms_code: form.smsCode })
    ElMessage.success('手机号已更换')
    currentPhone.value = form.phone
    localStorage.setItem('user', JSON.stringify({ phone: form.phone }))
    changing.value = false
    form.phone = ''
    form.smsCode = ''
  } catch { /* ignore */ }
}

function cancelChange() {
  changing.value = false
  form.phone = ''
  form.smsCode = ''
}

onMounted(loadProfile)
</script>

<template>
  <div class="profile-page">
    <el-card shadow="never">
      <template #header>个人信息</template>

      <!-- 当前信息 -->
      <el-form v-if="!changing" label-width="80px" style="max-width: 480px">
        <el-form-item label="手机号">
          <span style="font-size: 16px; font-weight: 500">{{ currentPhone }}</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="changing = true">更换手机号</el-button>
        </el-form-item>
      </el-form>

      <!-- 更换手机号 -->
      <el-form v-else :model="form" label-width="100px" style="max-width: 480px">
        <el-form-item label="原手机号">
          <span style="color: #999">{{ currentPhone }}</span>
        </el-form-item>
        <el-form-item label="新手机号">
          <el-input v-model="form.phone" placeholder="输入新手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="验证码">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-input v-model="form.smsCode" placeholder="6位验证码" maxlength="6" style="flex: 1" />
            <el-button :disabled="smsCountdown > 0 || !form.phone" @click="sendSms">
              {{ smsCountdown > 0 ? `${smsCountdown}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="changePhone">确认更换</el-button>
          <el-button @click="cancelChange">取消</el-button>
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

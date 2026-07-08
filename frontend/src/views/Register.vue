<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'

const router = useRouter()
const step = ref(1)
const smsCountdown = ref(0)
const submitting = ref(false)

const form = reactive({
  phone: '',
  password: '',
  passwordConfirm: '',
  smsCode: '',
  captchaSessionKey: '',
  captchaAnswer: '',
})

const captcha = reactive({
  session_key: '',
  question: '',
})

async function sendSms() {
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    ElMessage.warning('请输入有效的手机号')
    return
  }
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
  } catch { /* error handled by interceptor */ }
}

async function getCaptcha() {
  try {
    const data = await authApi.getCaptcha()
    captcha.session_key = data.session_key
    captcha.question = data.question
  } catch { /* ignore */ }
}

function nextStep() {
  if (step.value === 1) {
    if (!/^1[3-9]\d{9}$/.test(form.phone)) { ElMessage.warning('请输入有效的手机号'); return }
    if (form.password.length < 6) { ElMessage.warning('密码至少6位'); return }
    if (form.password !== form.passwordConfirm) { ElMessage.warning('两次密码不一致'); return }
    step.value = 2
    getCaptcha()
  }
}

async function doRegister() {
  if (!form.smsCode) { ElMessage.warning('请输入短信验证码'); return }
  if (!form.captchaAnswer) { ElMessage.warning('请输入数学验证码'); return }

  submitting.value = true
  try {
    await authApi.register({
      phone: form.phone,
      password: form.password,
      password_confirm: form.passwordConfirm,
      sms_code: form.smsCode,
      captcha_session_key: captcha.session_key,
      captcha_answer: form.captchaAnswer,
    })
    step.value = 3
    setTimeout(() => router.push('/login'), 3000)
  } catch { /* error handled by interceptor */ }
  finally { submitting.value = false }
}
</script>

<template>
  <div class="register-page">
    <el-card class="register-card" shadow="hover">
      <template #header><div class="title">用户注册</div></template>

      <el-steps :active="step - 1" finish-status="success" align-center style="margin-bottom: 24px">
        <el-step title="填写信息" />
        <el-step title="验证身份" />
        <el-step title="完成" />
      </el-steps>

      <!-- Step 1 -->
      <el-form v-if="step === 1" :model="form" label-width="88px" @submit.prevent="nextStep">
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="请输入手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.passwordConfirm" type="password" show-password placeholder="再次输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" style="width: 100%">下一步</el-button>
        </el-form-item>
      </el-form>

      <!-- Step 2 -->
      <el-form v-if="step === 2" :model="form" label-width="88px" @submit.prevent="doRegister">
        <el-form-item label="短信验证码">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-input v-model="form.smsCode" placeholder="6位验证码" maxlength="6" style="flex: 1" />
            <el-button :disabled="smsCountdown > 0" @click="sendSms">
              {{ smsCountdown > 0 ? `${smsCountdown}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="数学验证">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-tag size="large" type="warning" style="font-size: 18px; padding: 8px 16px; line-height: 32px">
              {{ captcha.question || '加载中...' }}
            </el-tag>
            <el-input v-model="form.captchaAnswer" placeholder="输入答案" style="flex: 1" />
          </div>
        </el-form-item>
        <el-form-item>
          <el-button @click="step = 1">上一步</el-button>
          <el-button type="primary" native-type="submit" :loading="submitting">注册</el-button>
        </el-form-item>
      </el-form>

      <!-- Step 3: Done -->
      <div v-if="step === 3" style="text-align: center; padding: 40px 0">
        <el-icon style="font-size: 60px; color: var(--el-color-success)"><CircleCheckFilled /></el-icon>
        <p style="font-size: 18px; margin-top: 16px">注册成功！</p>
        <p style="color: #999">即将跳转到登录页...</p>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.register-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #e8f3ff 0%, #f5f7fa 100%);
}

.register-card {
  width: 480px;
}

.title {
  text-align: center;
  font-size: 18px;
  font-weight: 600;
}
</style>

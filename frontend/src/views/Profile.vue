<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'

const currentPhone = ref('')
const dingtalkUserId = ref('')
const dingtalkMobile = ref('')
const supervisorDingtalkUserId = ref('')
const supervisorDingtalkMobile = ref('')
const changing = ref(false)
const smsCountdown = ref(0)
const savingProfile = ref(false)

const form = reactive({
  phone: '',
  smsCode: '',
})

async function loadProfile() {
  try {
    const data = await authApi.getMe()
    currentPhone.value = data.phone || ''
    dingtalkUserId.value = data.dingtalk_user_id || ''
    dingtalkMobile.value = data.dingtalk_mobile || ''
    supervisorDingtalkUserId.value = data.supervisor_dingtalk_user_id || ''
    supervisorDingtalkMobile.value = data.supervisor_dingtalk_mobile || ''
    localStorage.setItem('user', JSON.stringify({ phone: data.phone, id: data.id }))
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

async function saveProfile() {
  savingProfile.value = true
  try {
    await authApi.updateProfile({
      dingtalk_user_id: dingtalkUserId.value,
      dingtalk_mobile: dingtalkMobile.value,
      supervisor_dingtalk_user_id: supervisorDingtalkUserId.value,
      supervisor_dingtalk_mobile: supervisorDingtalkMobile.value,
    })
    ElMessage.success('个人信息已保存')
  } catch (err) {
    ElMessage.error(err?.response?.data?.error || '保存失败')
  } finally {
    savingProfile.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <div class="profile-page">
    <el-card shadow="never">
      <template #header>个人信息</template>

      <el-form v-if="!changing" label-width="120px" style="max-width: 520px">
        <el-form-item label="手机号">
          <span style="font-size: 16px; font-weight: 500">{{ currentPhone }}</span>
        </el-form-item>

        <el-divider content-position="left">我的钉钉（首次通知 @ 我）</el-divider>

        <el-form-item label="钉钉 UserID">
          <el-input v-model="dingtalkUserId" placeholder="钉钉企业内部 UserID" />
        </el-form-item>
        <el-form-item label="钉钉手机号">
          <el-input v-model="dingtalkMobile" placeholder="可选，与 UserID 二选一或同时填" />
        </el-form-item>

        <el-divider content-position="left">上级钉钉（超时升级 @ 上级）</el-divider>

        <el-form-item label="上级 UserID">
          <el-input v-model="supervisorDingtalkUserId" placeholder="上级的钉钉 UserID，无需对方注册账号" />
        </el-form-item>
        <el-form-item label="上级手机号">
          <el-input v-model="supervisorDingtalkMobile" placeholder="可选，用于 @ 上级手机号" />
        </el-form-item>
        <el-form-item>
          <div style="color: #999; font-size: 12px; line-height: 1.6">
            告警超时未处理时，系统会向群推送升级消息并 @ 上级。<br>
            上级不必是本系统用户，填对方的钉钉 UserID 即可。
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存</el-button>
          <el-button @click="changing = true">更换手机号</el-button>
        </el-form-item>
      </el-form>

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

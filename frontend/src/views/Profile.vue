<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi, householdApi } from '@/api'

const currentPhone = ref('')
const currentUserId = ref(null)
const dingtalkUserId = ref('')
const dingtalkMobile = ref('')
const supervisorId = ref(null)
const supervisorOptions = ref([])
const changing = ref(false)
const smsCountdown = ref(0)
const savingProfile = ref(false)

const form = reactive({
  phone: '',
  smsCode: '',
})

async function loadSupervisorOptions(householdId) {
  if (!householdId) {
    supervisorOptions.value = []
    return
  }
  try {
    const members = await householdApi.getMembers(householdId)
    supervisorOptions.value = (members || [])
      .filter((m) => m.user_id !== currentUserId.value)
      .map((m) => ({
        value: m.user_id,
        label: `${m.user_phone}${m.role === 'admin' ? '（管理员）' : ''}`,
      }))
  } catch {
    supervisorOptions.value = []
  }
}

async function loadProfile() {
  try {
    const data = await authApi.getMe()
    currentUserId.value = data.id
    currentPhone.value = data.phone || ''
    dingtalkUserId.value = data.dingtalk_user_id || ''
    dingtalkMobile.value = data.dingtalk_mobile || ''
    supervisorId.value = data.supervisor_id || null
    localStorage.setItem('user', JSON.stringify({ phone: data.phone, id: data.id }))

    const householdId = localStorage.getItem('activeHouseholdId')
      || data.households?.[0]?.id
    await loadSupervisorOptions(householdId)
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
    localStorage.setItem('user', JSON.stringify({ phone: form.phone, id: currentUserId.value }))
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
      supervisor_id: supervisorId.value,
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

      <!-- 当前信息 -->
      <el-form v-if="!changing" label-width="100px" style="max-width: 480px">
        <el-form-item label="手机号">
          <span style="font-size: 16px; font-weight: 500">{{ currentPhone }}</span>
        </el-form-item>
        <el-form-item label="钉钉 UserID">
          <el-input v-model="dingtalkUserId" placeholder="钉钉企业内部UserID，用于@提醒" />
        </el-form-item>
        <el-form-item label="钉钉手机号">
          <el-input v-model="dingtalkMobile" placeholder="如与登录手机号不同，用于@提醒" />
        </el-form-item>
        <el-form-item label="直属上级">
          <el-select
            v-model="supervisorId"
            clearable
            placeholder="选择告警升级时的上级（同家庭成员）"
            style="width: 100%"
          >
            <el-option
              v-for="opt in supervisorOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <div style="color: #999; font-size: 12px; margin-top: 4px">
            告警超时未处理时将通知上级；未填钉钉 UserID 时仍发群消息，只是不 @
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存</el-button>
          <el-button @click="changing = true">更换手机号</el-button>
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

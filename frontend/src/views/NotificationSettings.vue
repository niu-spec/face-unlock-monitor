<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { notificationApi } from '@/api'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const config = ref({
  webhook_url: '',
  secret: '',
  is_enabled: false,
  escalation_timeout_high: 60,
  escalation_timeout_medium: 300,
  escalation_timeout_low: 900,
  default_assignee: null,
})

async function loadConfig() {
  loading.value = true
  try {
    const data = await notificationApi.getConfig()
    config.value = data
  } catch {
    ElMessage.error('加载通知配置失败')
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    await notificationApi.updateConfig(config.value)
    ElMessage.success('通知配置已保存')
  } catch {
    ElMessage.error('保存通知配置失败')
  } finally {
    saving.value = false
  }
}

async function testWebhook() {
  if (!config.value.webhook_url) {
    ElMessage.warning('请先填写 Webhook 地址')
    return
  }
  testing.value = true
  try {
    // 先保存再测试
    await notificationApi.updateConfig(config.value)
    const res = await notificationApi.testWebhook()
    ElMessage.success(res.message || '测试消息发送成功')
  } catch (err) {
    const msg = err?.response?.data?.error || '测试消息发送失败，请检查 Webhook 地址和 Secret'
    ElMessage.error(msg)
  } finally {
    testing.value = false
  }
}

onMounted(loadConfig)
</script>

<template>
  <el-card shadow="never" v-loading="loading">
    <template #header>
      <span>钉钉通知设置</span>
    </template>

    <el-form label-width="180px" style="max-width: 640px">
      <el-form-item label="启用通知">
        <el-switch v-model="config.is_enabled" />
        <span style="margin-left: 8px; color: #999; font-size: 12px">
          关闭后该家庭告警不再推送钉钉
        </span>
      </el-form-item>

      <el-divider />

      <el-form-item label="Webhook 地址">
        <el-input v-model="config.webhook_url" placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx" />
        <div style="color: #999; font-size: 12px; margin-top: 4px">
          在钉钉群 → 群设置 → 智能群助手 → 添加机器人 → 自定义 → 获取 Webhook 地址
        </div>
      </el-form-item>

      <el-form-item label="加签密钥 (Secret)">
        <el-input v-model="config.secret" type="password" show-password placeholder="选填，安全设置中的加签密钥" />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="saveConfig">
          保存配置
        </el-button>
        <el-button type="success" :loading="testing" @click="testWebhook">
          保存并测试
        </el-button>
      </el-form-item>

      <el-divider content-position="left">升级超时设置</el-divider>

      <el-form-item label="HIGH 级别超时">
        <el-input-number v-model="config.escalation_timeout_high" :min="10" :max="3600" :step="10" />
        <span style="margin-left: 8px; color: #999; font-size: 12px">秒（默认 60 秒）</span>
      </el-form-item>

      <el-form-item label="MEDIUM 级别超时">
        <el-input-number v-model="config.escalation_timeout_medium" :min="30" :max="7200" :step="30" />
        <span style="margin-left: 8px; color: #999; font-size: 12px">秒（默认 300 秒 = 5 分钟）</span>
      </el-form-item>

      <el-form-item label="LOW 级别超时">
        <el-input-number v-model="config.escalation_timeout_low" :min="60" :max="43200" :step="60" />
        <span style="margin-left: 8px; color: #999; font-size: 12px">秒（默认 900 秒 = 15 分钟）</span>
      </el-form-item>

    </el-form>
  </el-card>
</template>

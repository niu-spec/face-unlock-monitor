<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getPublicBaseUrl } from '@/utils/device'

const qrDataUrl = ref('')
const registerUrl = computed(() => `${getPublicBaseUrl()}/family?from=mobile`)

async function buildQr() {
  try {
    const QRCode = await import('qrcode')
    qrDataUrl.value = await QRCode.toDataURL(registerUrl.value, {
      width: 200,
      margin: 1,
    })
  } catch {
    qrDataUrl.value = ''
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(registerUrl.value)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.error('复制失败，请手动复制链接')
  }
}

onMounted(buildQr)
</script>

<template>
  <div class="mobile-register-qr">
    <img v-if="qrDataUrl" :src="qrDataUrl" alt="手机录入二维码" class="qr-image" />
    <div v-else class="qr-fallback">二维码生成中…</div>
    <p class="qr-url">{{ registerUrl }}</p>
    <el-button size="small" @click="copyLink">复制链接</el-button>
    <ol class="qr-steps">
      <li>管理员用手机浏览器扫码或打开链接</li>
      <li>登录同一账号，并在「家庭管理」选中当前家庭</li>
      <li>对准被录入人，用后置摄像头截取人脸后提交</li>
    </ol>
    <p class="qr-note">
      若扫码后无法打开，请确认手机能访问该地址（云上部署用公网 IP/域名；本地开发需同一 WiFi 且使用电脑局域网 IP）。
    </p>
  </div>
</template>

<style scoped>
.mobile-register-qr {
  padding: 12px;
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  background: #fafafa;
}

.qr-image,
.qr-fallback {
  display: block;
  width: 200px;
  height: 200px;
  margin: 0 auto 8px;
}

.qr-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 13px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
}

.qr-url {
  margin: 0 0 8px;
  text-align: center;
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}

.qr-steps {
  margin: 12px 0 0;
  padding-left: 18px;
  color: #606266;
  font-size: 13px;
  line-height: 1.7;
}

.qr-note {
  margin: 8px 0 0;
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
}
</style>

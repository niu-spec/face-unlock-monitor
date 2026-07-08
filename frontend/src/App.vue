<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { householdApi, authApi } from '@/api'

const route = useRoute()
const router = useRouter()

const isLoginPage = computed(() => route.path === '/login' || route.path === '/register')
const pendingTotal = ref(0)  // 全局待审核总数
let pollTimer = null

// 从 localStorage 读取用户信息，确保登录/退出后都能正确显示
function getUserDisplayName() {
  const cachedUser = JSON.parse(localStorage.getItem('user') || '{}')
  return cachedUser.phone || ''
}
const displayName = ref(getUserDisplayName())

// 监听路由变化：从登录页 → 主页时刷新 displayName
watch(() => route.path, (newPath) => {
  if (newPath !== '/login' && newPath !== '/register') {
    displayName.value = getUserDisplayName()
  }
})

async function logout() {
  // 先调用后端注销接口，让 refresh token 进入黑名单
  const refresh = localStorage.getItem('refresh')
  if (refresh) {
    try {
      await authApi.logout(refresh)
    } catch { /* 后端调用失败不影响前端清理 */ }
  }

  // 清除所有 localStorage 数据
  localStorage.removeItem('token')
  localStorage.removeItem('refresh')
  localStorage.removeItem('activeHouseholdId')
  localStorage.removeItem('user')
  localStorage.removeItem('households')

  // 清除状态
  displayName.value = ''
  pendingTotal.value = 0

  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  router.push('/login')
}

// 全局轮询：检查是否有新的加入申请
async function checkApplications() {
  const token = localStorage.getItem('token')
  if (!token) return

  let total = 0
  let newApps = []

  try {
    const data = await householdApi.list()
    const households = data.results || data
    for (const h of households) {
      if (h.is_admin) {
        try {
          const apps = await householdApi.getApplications(h.id)
          const count = (apps || []).length
          if (count > 0) {
            total += count
            newApps.push({ household: h.name, count })
          }
        } catch { /* ignore */ }
      }
    }
  } catch { return }

  // 发现新申请 → 弹窗通知
  if (total > pendingTotal.value && pendingTotal.value > 0 && newApps.length > 0) {
    const names = newApps.map(a => `「${a.household}」${a.count}条`).join('、')
    ElNotification({
      title: '新的加入申请',
      message: `${names}`,
      type: 'info',
      duration: 5000,
      onClick: () => router.push('/households'),
    })
  }

  pendingTotal.value = total
}

function startPolling() {
  if (pollTimer) return
  checkApplications()
  pollTimer = setInterval(checkApplications, 10000)  // 每10秒检查
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 监听 token 变化（登录/退出）来控制轮询
watch(() => localStorage.getItem('token'), (newToken) => {
  if (newToken) {
    startPolling()
  } else {
    stopPolling()
  }
}, { immediate: false })

onMounted(() => {
  if (localStorage.getItem('token')) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})

const menuItems = [
  { path: '/monitor', title: '居家监控', icon: 'Monitor' },
  { path: '/family', title: '家人注册', icon: 'UserFilled' },
  { path: '/zones', title: '危险区域', icon: 'Crop' },
  { path: '/alerts', title: '告警中心', icon: 'Bell' },
  { path: '/events', title: '事件记录', icon: 'Document' },
  { path: '/households', title: '家庭管理', icon: 'Setting' },
  { path: '/profile', title: '个人信息', icon: 'UserFilled' },
]

const activeMenu = computed(() => route.path)
</script>

<template>
  <router-view v-if="isLoginPage" />

  <el-container v-else class="layout">
    <el-aside width="220px" class="aside">
      <div class="brand">
        <el-icon><VideoCamera /></el-icon>
        <span>居家监控</span>
      </div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
          <el-badge
            v-if="item.path === '/households' && pendingTotal > 0"
            :value="pendingTotal"
            style="margin-left: 8px"
          />
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span>{{ route.meta.title }}</span>
        <div style="display:flex;align-items:center;gap:12px">
          <span style="color:#666;font-size:14px">{{ displayName }}</span>
          <el-button text type="primary" @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}

.aside {
  border-right: 1px solid var(--el-border-color-light);
  background: #fff;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 60px;
  padding: 0 20px;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color-light);
  background: #fff;
}

.main {
  background: #f5f7fa;
}
</style>

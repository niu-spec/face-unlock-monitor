<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { householdApi } from '@/api'

const route = useRoute()
const router = useRouter()

const isLoginPage = computed(() => route.path === '/login' || route.path === '/register')
const pendingTotal = ref(0)  // 全局待审核总数
let pollTimer = null

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('refresh')
  localStorage.removeItem('activeHouseholdId')
  localStorage.removeItem('user')
  localStorage.removeItem('households')
  if (pollTimer) clearInterval(pollTimer)
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

onMounted(() => {
  checkApplications()
  pollTimer = setInterval(checkApplications, 10000)  // 每10秒检查
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// 读取本地缓存的用户信息
const cachedUser = JSON.parse(localStorage.getItem('user') || '{}')
const displayName = ref(cachedUser.nickname || cachedUser.phone || '')

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

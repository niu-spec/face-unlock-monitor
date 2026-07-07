<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const isLoginPage = computed(() => route.path === '/login' || route.path === '/register')

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('refresh')
  localStorage.removeItem('activeHouseholdId')
  localStorage.removeItem('user')
  localStorage.removeItem('households')
  router.push('/login')
}

const menuItems = [
  { path: '/monitor', title: '居家监控', icon: 'Monitor' },
  { path: '/family', title: '家人注册', icon: 'UserFilled' },
  { path: '/zones', title: '危险区域', icon: 'Crop' },
  { path: '/alerts', title: '告警中心', icon: 'Bell' },
  { path: '/events', title: '事件记录', icon: 'Document' },
  { path: '/households', title: '家庭管理', icon: 'Setting' },
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
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span>{{ route.meta.title }}</span>
        <el-button text type="primary" @click="logout">退出登录</el-button>
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

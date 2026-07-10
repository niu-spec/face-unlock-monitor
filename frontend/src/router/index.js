import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/monitor' },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { title: '注册', public: true },
  },
  {
    path: '/monitor',
    name: 'HomeMonitor',
    component: () => import('@/views/HomeMonitor.vue'),
    meta: { title: '居家监控' },
  },
  {
    path: '/family',
    name: 'FamilyRegister',
    component: () => import('@/views/FamilyRegister.vue'),
    meta: { title: '家人注册' },
  },
  {
    path: '/zones',
    name: 'ZoneEditor',
    component: () => import('@/views/ZoneEditor.vue'),
    meta: { title: '危险区域' },
  },
  {
    path: '/alerts',
    name: 'AlertCenter',
    component: () => import('@/views/AlertCenter.vue'),
    meta: { title: '告警中心' },
  },
  {
    path: '/events',
    name: 'EventLog',
    component: () => import('@/views/EventLog.vue'),
    meta: { title: '事件记录' },
  },
  {
    path: '/reports',
    name: 'DailyReport',
    component: () => import('@/views/DailyReport.vue'),
    meta: { title: '监控日报' },
  },
  {
    path: '/users',
    name: 'UserManage',
    component: () => import('@/views/UserManage.vue'),
    meta: { title: '用户管理' },
  },
  {
    path: '/households',
    name: 'HouseholdManage',
    component: () => import('@/views/HouseholdManage.vue'),
    meta: { title: '家庭管理' },
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { title: '个人信息' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '居家监控'} · home-camera-monitor`

  const isPublic = to.meta.public === true
  const token = localStorage.getItem('token')

  if (!isPublic && !token) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  if (to.path === '/login' && token) {
    return next({ path: '/monitor' })
  }

  next()
})

export default router

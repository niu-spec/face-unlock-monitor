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
    path: '/users',
    name: 'UserManage',
    component: () => import('@/views/UserManage.vue'),
    meta: { title: '用户管理' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || '居家监控'} · home-camera-monitor`
})

export default router

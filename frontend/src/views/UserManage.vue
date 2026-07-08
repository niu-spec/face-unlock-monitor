<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi, householdApi } from '@/api'

const router = useRouter()
const loading = ref(false)
const user = ref({ phone: '' })
const activeHousehold = ref(null)

async function loadUserManage() {
  loading.value = true
  try {
    const me = await authApi.getMe()
    user.value = me
    localStorage.setItem('user', JSON.stringify({ phone: me.phone }))

    const data = await householdApi.list()
    const households = data.results || data
    const activeId = Number(localStorage.getItem('activeHouseholdId'))
    activeHousehold.value =
      households.find((h) => h.id === activeId) || households[0] || null
  } catch {
    ElMessage.error('加载用户信息失败，请重新登录')
  } finally {
    loading.value = false
  }
}

onMounted(loadUserManage)
</script>

<template>
  <div v-loading="loading" class="user-manage-page">
    <el-card shadow="never">
      <template #header>用户管理</template>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="手机号">
          {{ user.phone || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="当前家庭">
          {{ activeHousehold?.name || '未加入家庭' }}
        </el-descriptions-item>
        <el-descriptions-item label="家庭角色">
          <template v-if="activeHousehold">
            {{ activeHousehold.is_admin ? '管理员' : '成员' }}
          </template>
          <template v-else>—</template>
        </el-descriptions-item>
      </el-descriptions>

      <div class="actions">
        <el-button type="primary" @click="router.push('/profile')">
          编辑个人信息
        </el-button>
        <el-button @click="router.push('/households')">
          家庭管理
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.user-manage-page {
  max-width: 640px;
  margin: 0 auto;
}

.actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>

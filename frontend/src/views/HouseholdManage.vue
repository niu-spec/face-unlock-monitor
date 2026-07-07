<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { householdApi } from '@/api'

const households = ref([])
const activeId = ref(Number(localStorage.getItem('activeHouseholdId')) || 0)
const activeTab = ref('my')
const showCreateDialog = ref(false)
const showJoinDialog = ref(false)
const newName = ref('')
const joinHouseholdId = ref('')
const joinMessage = ref('')

// 成员管理
const showMembersDialog = ref(false)
const currentMembers = ref([])
const currentHouseholdId = ref(0)

// 申请列表
const showApplicationsDialog = ref(false)
const currentApplications = ref([])

async function loadHouseholds() {
  try {
    const data = await householdApi.list()
    households.value = data.results || data
  } catch { /* ignore */ }
}

function switchHousehold(household) {
  activeId.value = household.id
  localStorage.setItem('activeHouseholdId', household.id)
  ElMessage.success(`已切换到「${household.name}」`)
}

async function createHousehold() {
  if (!newName.value.trim()) { ElMessage.warning('请输入家庭名称'); return }
  try {
    const data = await householdApi.create({ name: newName.value.trim() })
    ElMessage.success(`家庭「${data.name}」创建成功`)
    showCreateDialog.value = false
    newName.value = ''
    await loadHouseholds()
  } catch { /* ignore */ }
}

async function deleteHousehold(household) {
  try {
    await ElMessageBox.confirm(`确定要删除「${household.name}」吗？`, '确认删除', { type: 'warning' })
    await householdApi.remove(household.id)
    if (activeId.value === household.id) {
      activeId.value = 0
      localStorage.removeItem('activeHouseholdId')
    }
    ElMessage.success('已删除')
    await loadHouseholds()
  } catch { /* ignore */ }
}

async function loadMembers(household) {
  currentHouseholdId.value = household.id
  try {
    const data = await householdApi.getMembers(household.id)
    currentMembers.value = data
    showMembersDialog.value = true
  } catch { /* ignore */ }
}

async function kickMember(member) {
  try {
    await ElMessageBox.confirm(`确定要移除 ${member.user_phone} 吗？`, '确认', { type: 'warning' })
    await householdApi.kickMember(currentHouseholdId.value, member.user_id)
    ElMessage.success('已移除')
    await loadMembers({ id: currentHouseholdId.value })
  } catch { /* ignore */ }
}

async function transferAdmin(member) {
  try {
    await ElMessageBox.confirm(`确定将管理员转让给 ${member.user_phone} 吗？`, '确认', { type: 'warning' })
    await householdApi.transferAdmin(currentHouseholdId.value, member.user_id)
    ElMessage.success('管理员已转让')
    await loadMembers({ id: currentHouseholdId.value })
    await loadHouseholds()
  } catch { /* ignore */ }
}

async function loadApplications(household) {
  currentHouseholdId.value = household.id
  try {
    const data = await householdApi.getApplications(household.id)
    currentApplications.value = data
    showApplicationsDialog.value = true
  } catch { /* ignore */ }
}

async function reviewApp(app, action) {
  try {
    await householdApi.reviewApplication(currentHouseholdId.value, app.id, action)
    ElMessage.success(action === 'approve' ? '已通过' : '已拒绝')
    await loadApplications({ id: currentHouseholdId.value })
    await loadHouseholds()
  } catch { /* ignore */ }
}

async function applyJoin() {
  if (!joinHouseholdId.value) { ElMessage.warning('请输入家庭ID'); return }
  try {
    await householdApi.applyJoin({ household_id: Number(joinHouseholdId.value), message: joinMessage.value })
    ElMessage.success('申请已提交，等待管理员审核')
    showJoinDialog.value = false
  } catch { /* ignore */ }
}

const isCurrentAdmin = (h) => h.is_admin

onMounted(loadHouseholds)
</script>

<template>
  <div class="household-page">
    <el-tabs v-model="activeTab">
      <!-- 我的家庭 -->
      <el-tab-pane label="我的家庭" name="my">
        <div class="toolbar">
          <el-button type="primary" @click="showCreateDialog = true">创建新家庭</el-button>
          <el-button @click="showJoinDialog = true">申请加入</el-button>
        </div>

        <el-table :data="households" style="margin-top: 16px">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="家庭名称" />
          <el-table-column label="角色" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_admin ? 'primary' : 'info'" size="small">
                {{ row.is_admin ? '管理员' : '成员' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.id === activeId" type="success" size="small">当前</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="300">
            <template #default="{ row }">
              <el-button v-if="row.id !== activeId" size="small" type="primary" @click="switchHousehold(row)">切换</el-button>
              <el-button size="small" @click="loadMembers(row)">成员</el-button>
              <el-button v-if="row.is_admin" size="small" type="warning" @click="loadApplications(row)">审核</el-button>
              <el-button v-if="row.is_admin" size="small" type="danger" @click="deleteHousehold(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 创建家庭对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建新家庭" width="400px">
      <el-input v-model="newName" placeholder="家庭名称，如：张三家" />
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createHousehold">创建</el-button>
      </template>
    </el-dialog>

    <!-- 申请加入对话框 -->
    <el-dialog v-model="showJoinDialog" title="申请加入家庭" width="400px">
      <el-form label-width="80px">
        <el-form-item label="家庭ID">
          <el-input v-model="joinHouseholdId" placeholder="输入家庭ID" />
        </el-form-item>
        <el-form-item label="留言">
          <el-input v-model="joinMessage" type="textarea" placeholder="可选：介绍自己" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showJoinDialog = false">取消</el-button>
        <el-button type="primary" @click="applyJoin">提交申请</el-button>
      </template>
    </el-dialog>

    <!-- 成员管理对话框 -->
    <el-dialog v-model="showMembersDialog" title="成员管理" width="500px">
      <el-table :data="currentMembers">
        <el-table-column prop="user_phone" label="手机号" width="140" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'primary' : 'info'" size="small">
              {{ row.role === 'admin' ? '管理员' : '成员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="joined_at" label="加入时间" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button v-if="row.role === 'member'" size="small" type="primary" @click="transferAdmin(row)">转让管理员</el-button>
            <el-button v-if="row.role !== 'admin'" size="small" type="danger" @click="kickMember(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 审核申请对话框 -->
    <el-dialog v-model="showApplicationsDialog" title="审核加入申请" width="500px">
      <el-table :data="currentApplications">
        <el-table-column prop="applicant_phone" label="申请人" width="140" />
        <el-table-column prop="message" label="留言" />
        <el-table-column prop="created_at" label="申请时间" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="reviewApp(row, 'approve')">通过</el-button>
            <el-button size="small" type="danger" @click="reviewApp(row, 'reject')">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="currentApplications.length === 0" description="暂无待审核申请" />
    </el-dialog>
  </div>
</template>

<style scoped>
.household-page {
  max-width: 900px;
  margin: 0 auto;
}

.toolbar {
  display: flex;
  gap: 8px;
}
</style>

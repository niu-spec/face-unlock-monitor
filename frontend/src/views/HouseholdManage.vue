<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { householdApi, memberApi } from '@/api'

const households = ref([])
const loading = ref(false)
const activeId = ref(Number(localStorage.getItem('activeHouseholdId')) || 0)
const showCreateDialog = ref(false)
const showJoinDialog = ref(false)
const newName = ref('')
const joinHouseholdId = ref('')
const joinMessage = ref('')

// 当前进入的家庭
const enteredHousehold = ref(null)
const householdMembers = ref([])
const showMembersDialog = ref(false)
const currentMembers = ref([])
const editingMember = ref(null)
const editMemberForm = ref({ name: '', identity: '', role: 'adult' })
const showApplicationsDialog = ref(false)
const currentApplications = ref([])
const currentHouseholdId = ref(0)

// 待审核数
const pendingCounts = ref({})

async function loadHouseholds() {
  loading.value = true
  try {
    const data = await householdApi.list()
    households.value = data.results || data
    if (households.value.length === 0) {
      ElMessage.info('您还没有加入任何家庭，请创建或申请加入一个家庭')
    }
    for (const h of households.value) {
      if (h.is_admin) {
        try {
          const apps = await householdApi.getApplications(h.id)
          pendingCounts.value[h.id] = (apps || []).length
        } catch { pendingCounts.value[h.id] = 0 }
      }
    }
  } catch (err) {
    ElMessage.error('加载家庭列表失败，请检查网络或重新登录')
    console.error('加载家庭列表失败:', err)
  } finally {
    loading.value = false
  }
}

function switchHousehold(household) {
  activeId.value = household.id
  localStorage.setItem('activeHouseholdId', household.id)
  ElMessage.success(`已切换到「${household.name}」`)
}

function enterHousehold(household) {
  switchHousehold(household)
  enteredHousehold.value = household
  loadHouseholdMembers(household.id)
}

async function loadHouseholdMembers(householdId) {
  // 确保 activeHouseholdId 已更新，以便 interceptor 发送正确的 header
  localStorage.setItem('activeHouseholdId', householdId)
  activeId.value = householdId
  try {
    const data = await memberApi.list()
    householdMembers.value = data.results || data
  } catch (err) {
    ElMessage.error('加载家庭成员失败，请确认该家庭中有成员数据')
    console.error('加载家庭成员失败:', err)
    householdMembers.value = []
  }
}

async function createHousehold() {
  if (!newName.value.trim()) { ElMessage.warning('请输入家庭名称'); return }
  try {
    const data = await householdApi.create({ name: newName.value.trim() })
    ElMessage.success(`家庭「${data.name}」创建成功`)
    showCreateDialog.value = false
    newName.value = ''
    await loadHouseholds()
  } catch (err) {
    ElMessage.error('创建家庭失败，请重试')
    console.error('创建家庭失败:', err)
  }
}

async function deleteHousehold(household) {
  try {
    await ElMessageBox.confirm(`确定要删除「${household.name}」吗？`, '确认删除', { type: 'warning' })
    await householdApi.remove(household.id)
    if (activeId.value === household.id) {
      activeId.value = 0
      localStorage.removeItem('activeHouseholdId')
    }
    if (enteredHousehold.value?.id === household.id) enteredHousehold.value = null
    delete pendingCounts.value[household.id]
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
    if (data.length === 0) {
      ElMessage.info('该家庭暂无成员')
    }
  } catch (err) {
    ElMessage.error('加载成员列表失败，请重试')
    console.error('加载成员列表失败:', err)
  }
}

function startEditMember(member) {
  editingMember.value = member
  editMemberForm.value = { name: member.name, identity: member.identity || '', role: member.role }
}

async function saveEditMember() {
  if (!editingMember.value) return
  try {
    await memberApi.update(editingMember.value.id, editMemberForm.value)
    ElMessage.success('已更新')
    editingMember.value = null
    loadHouseholdMembers(enteredHousehold.value.id)
  } catch { /* ignore */ }
}

function cancelEdit() { editingMember.value = null }

async function removeHouseholdMember(member) {
  try {
    await ElMessageBox.confirm(`确定删除「${member.name}」？`, '确认', { type: 'warning' })
    await memberApi.remove(member.id)
    ElMessage.success('已删除')
    loadHouseholdMembers(enteredHousehold.value.id)
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
    pendingCounts.value[household.id] = 0
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
    joinMessage.value = ''
  } catch { /* ignore */ }
}

onMounted(loadHouseholds)
</script>

<template>
  <el-card shadow="never" class="household-page">
    <template #header>
      <div class="header">
        <span>我的家庭</span>
        <div class="toolbar">
          <el-button type="primary" @click="showCreateDialog = true">创建新家庭</el-button>
          <el-button @click="showJoinDialog = true">申请加入</el-button>
        </div>
      </div>
    </template>

    <el-table :data="households" v-loading="loading" empty-text="暂无家庭数据">
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
          <el-table-column label="操作" min-width="280" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button size="small" type="success" @click="enterHousehold(row)">进入</el-button>
                <el-button v-if="row.id !== activeId" size="small" type="primary" plain @click="switchHousehold(row)">切换</el-button>
                <el-button size="small" plain @click="loadMembers(row)">成员管理</el-button>
                <el-badge v-if="row.is_admin" :value="pendingCounts[row.id] || 0" :hidden="!pendingCounts[row.id]">
                  <el-button size="small" type="warning" plain @click="loadApplications(row)">审核</el-button>
                </el-badge>
                <el-button v-if="row.is_admin" size="small" type="danger" plain @click="deleteHousehold(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loading && households.length === 0" description="暂无家庭，请创建新家庭或申请加入已有家庭" />

        <!-- 进入家庭后的成员管理面板 -->
        <div v-if="enteredHousehold" style="margin-top: 24px">
          <el-divider />
          <h3 style="margin-bottom: 12px">
            {{ enteredHousehold.name }} — 家庭成员
            <el-tag size="small" style="margin-left: 8px">{{ householdMembers.length }}人</el-tag>
          </h3>

          <el-table :data="householdMembers" stripe>
            <el-table-column label="姓名" min-width="100">
              <template #default="{ row: m }">
                <el-input
                  v-if="editingMember?.id === m.id"
                  v-model="editMemberForm.name"
                  size="small"
                  placeholder="姓名"
                />
                <span v-else>{{ m.name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="身份" width="120">
              <template #default="{ row: m }">
                <el-input
                  v-if="editingMember?.id === m.id"
                  v-model="editMemberForm.identity"
                  size="small"
                  placeholder="如：爸爸"
                />
                <span v-else>{{ m.identity || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="角色" width="120">
              <template #default="{ row: m }">
                <template v-if="editingMember?.id === m.id">
                  <el-select v-model="editMemberForm.role" size="small" style="width: 90px">
                    <el-option label="成人" value="adult" />
                    <el-option label="小孩" value="child" />
                    <el-option label="老人" value="elder" />
                    <el-option label="访客" value="guest" />
                  </el-select>
                </template>
                <el-tag v-else size="small">{{ m.role_display || m.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="人脸" width="80">
              <template #default="{ row: m }">
                <el-tag :type="m.face_encoding ? 'success' : 'info'" size="small">
                  {{ m.face_encoding ? '已录入' : '未录入' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row: m }">
                <template v-if="editingMember?.id === m.id">
                  <el-button size="small" type="primary" @click="saveEditMember">保存</el-button>
                  <el-button size="small" @click="cancelEdit">取消</el-button>
                </template>
                <template v-else>
                  <el-button size="small" link type="primary" @click="startEditMember(m)">编辑</el-button>
                  <el-button size="small" link type="danger" @click="removeHouseholdMember(m)">删除</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="householdMembers.length === 0" description="暂无家庭成员，请去「家人注册」页面录入" />
        </div>

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

    <!-- 成员管理对话框（成员关系） -->
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
  </el-card>
</template>

<style scoped>
.household-page { max-width: 950px; margin: 0 auto; }
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.toolbar { display: flex; gap: 8px; flex-shrink: 0; }
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.action-buttons :deep(.el-button) {
  margin: 0;
}
</style>

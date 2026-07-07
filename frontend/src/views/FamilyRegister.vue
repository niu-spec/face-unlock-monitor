<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { memberApi } from '@/api'

const form = reactive({
  name: '',
  role: 'adult',
  student_id: '',
})

const submitting = ref(false)

async function onSubmit() {
  if (!form.name.trim()) { ElMessage.warning('请输入姓名'); return }

  submitting.value = true
  try {
    await memberApi.create({
      name: form.name.trim(),
      role: form.role,
      student_id: form.student_id,
    })
    ElMessage.success('家庭成员已注册')
    form.name = ''
    form.student_id = ''
  } catch { /* error handled by interceptor */ }
  finally { submitting.value = false }
}
</script>

<template>
  <el-card shadow="never">
    <template #header>家庭成员录入</template>
    <el-form :model="form" label-width="88px" style="max-width: 480px">
      <el-form-item label="姓名">
        <el-input v-model="form.name" placeholder="如：爸爸" />
      </el-form-item>
      <el-form-item label="角色">
        <el-radio-group v-model="form.role">
          <el-radio value="adult">成人</el-radio>
          <el-radio value="child">小孩</el-radio>
          <el-radio value="elder">老人</el-radio>
          <el-radio value="guest">访客</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="学号/工号">
        <el-input v-model="form.student_id" placeholder="可选" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSubmit" :loading="submitting">录入成员</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

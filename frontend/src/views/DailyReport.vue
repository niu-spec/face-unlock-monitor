<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import EventReplayDialog from '@/components/EventReplayDialog.vue'
import { reportApi } from '@/api'

const loading = ref(false)
const generating = ref(false)
const reports = ref([])
const selectedId = ref(null)
const reportDate = ref('')
const replayVisible = ref(false)
const replayItem = ref(null)

const selectedReport = computed(() =>
  reports.value.find((item) => item.id === selectedId.value) ?? null,
)

const highlights = computed(() => selectedReport.value?.stats?.highlights || [])

const statsCards = computed(() => {
  const stats = selectedReport.value?.stats
  if (!stats) return []
  return [
    { label: '告警总数', value: stats.total_alerts ?? 0 },
    { label: '高等级', value: stats.high_alerts ?? 0 },
    { label: '待处理', value: stats.pending_alerts ?? 0 },
    { label: '事件日志', value: stats.total_events ?? 0 },
  ]
})

function todayString() {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

async function loadReports() {
  loading.value = true
  try {
    const data = await reportApi.list()
    reports.value = data.results || data
    if (!selectedId.value && reports.value.length) {
      selectedId.value = reports.value[0].id
    }
  } catch {
    reports.value = []
  } finally {
    loading.value = false
  }
}

async function generateReport() {
  generating.value = true
  try {
    const payload = reportDate.value ? { date: reportDate.value } : {}
    const report = await reportApi.generate(payload)
    ElMessage.success(report.source === 'ai' ? 'AI 日报已生成' : '日报已生成（规则模板）')
    await loadReports()
    selectedId.value = report.id
  } catch {
    ElMessage.error('日报生成失败，请确认已选择家庭')
  } finally {
    generating.value = false
  }
}

function downloadMarkdown() {
  const report = selectedReport.value
  if (!report?.summary) return

  const blob = new Blob([report.summary], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${report.title || '监控日报'}.md`
  link.click()
  URL.revokeObjectURL(url)
}

async function copyMarkdown() {
  const text = selectedReport.value?.summary
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

function openHighlightReplay(item) {
  replayItem.value = item
  replayVisible.value = true
}

function canReplayHighlight(item) {
  return Boolean(item?.snapshot_path || item?.clip_path)
}

onMounted(() => {
  reportDate.value = todayString()
  loadReports()
})
</script>

<template>
  <el-row :gutter="16">
    <el-col :span="8">
      <el-card shadow="never">
        <template #header>生成日报</template>
        <el-form label-width="80px">
          <el-form-item label="日期">
            <el-date-picker
              v-model="reportDate"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="generating" @click="generateReport">
              生成 AI 日报
            </el-button>
          </el-form-item>
        </el-form>
        <p class="hint">
          工作流：采集告警/事件 → 统计汇总 → AI 分析（未配置 API Key 时使用规则模板）。
        </p>

        <el-divider />

        <div class="history-title">历史日报</div>
        <el-table
          :data="reports"
          stripe
          v-loading="loading"
          highlight-current-row
          @current-change="(row) => { selectedId = row?.id ?? null }"
        >
          <el-table-column prop="report_date" label="日期" width="110" />
          <el-table-column label="来源" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.source === 'ai' ? 'success' : 'info'">
                {{ row.source_display || row.source }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-col>

    <el-col :span="16">
      <el-card shadow="never" v-loading="loading">
        <template #header>
          <div class="preview-header">
            <span>{{ selectedReport?.title || '日报预览' }}</span>
            <div v-if="selectedReport" class="preview-actions">
              <el-button link type="primary" @click="copyMarkdown">复制</el-button>
              <el-button link type="primary" @click="downloadMarkdown">下载 Markdown</el-button>
            </div>
          </div>
        </template>

        <el-row v-if="statsCards.length" :gutter="12" class="stats-row">
          <el-col v-for="item in statsCards" :key="item.label" :span="6">
            <div class="stat-card">
              <div class="stat-value">{{ item.value }}</div>
              <div class="stat-label">{{ item.label }}</div>
            </div>
          </el-col>
        </el-row>

        <el-card v-if="highlights.length" shadow="never" class="highlights-card">
          <template #header>重点事件回放</template>
          <el-table :data="highlights" stripe size="small">
            <el-table-column prop="created_at" label="时间" width="100" />
            <el-table-column prop="stream_label" label="摄像头" width="90" />
            <el-table-column prop="type_label" label="类型" width="110" />
            <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
            <el-table-column label="回放" width="80">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  :disabled="!canReplayHighlight(row)"
                  @click="openHighlightReplay(row)"
                >
                  回放
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <pre v-if="selectedReport" class="report-body">{{ selectedReport.summary }}</pre>
        <el-empty v-else description="请选择日期生成日报，或点击左侧历史记录" />
      </el-card>
    </el-col>
  </el-row>

  <EventReplayDialog
    v-model="replayVisible"
    :title="replayItem?.type_label || '事件回放'"
    :description="replayItem?.description || ''"
    :timestamp="replayItem?.created_at || ''"
    :stream-id="replayItem?.stream_label || replayItem?.stream_id || ''"
    :snapshot-path="replayItem?.snapshot_path || ''"
    :clip-path="replayItem?.clip_path || ''"
  />
</template>

<style scoped>
.hint {
  margin: 0;
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
}

.history-title {
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.stats-row {
  margin-bottom: 16px;
}

.highlights-card {
  margin-bottom: 16px;
}

.stat-card {
  padding: 12px;
  border-radius: 8px;
  background: #f5f7fa;
  text-align: center;
}

.stat-value {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.report-body {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
}
</style>

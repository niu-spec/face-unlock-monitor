<script setup>
import { ref } from 'vue'

const events = ref([])
</script>

<template>
  <el-card shadow="never">
    <template #header>事件记录</template>
    <el-timeline v-if="events.length">
      <el-timeline-item v-for="item in events" :key="item.id" :timestamp="item.created_at">
        {{ item.message }}
      </el-timeline-item>
    </el-timeline>
    <el-empty v-else description="暂无事件，联调 GET /api/events 后展示" />
  </el-card>
</template>

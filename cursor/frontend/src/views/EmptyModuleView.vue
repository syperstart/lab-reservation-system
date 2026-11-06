<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Box } from '@element-plus/icons-vue'

const route = useRoute()
const moduleName = computed(() => (route.meta.title as string) || '当前模块')
</script>

<template>
  <!-- 模块内容已清空，仅保留导航骨架与面包屑 -->
  <div class="empty-canvas">
    <div class="empty-hint">
      <span class="empty-icon">
        <el-icon :size="22"><Box /></el-icon>
      </span>
      <b>{{ moduleName }}</b>
      <span class="empty-text">模块内容待接入</span>
    </div>
  </div>
</template>

<style scoped>
.empty-canvas {
  display: grid;
  place-items: center;
  min-height: 100%;
}
.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #b9c3d2;
  text-align: center;
  user-select: none;
}
.empty-icon {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  margin-bottom: 6px;
  border-radius: 16px;
  background: #eef2f8;
}
.empty-hint b {
  font-size: 14px;
  font-weight: 500;
  color: #9aa7b9;
}
.empty-text {
  font-size: 12px;
  color: #c2cad7;
}
</style>

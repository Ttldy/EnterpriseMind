<script setup lang="ts">
import type { Citation } from "./types";

defineProps<{
  citation: Citation;
}>();
</script>

<template>
  <el-card class="citation-card" shadow="never">
    <div class="citation-title">
      <strong>{{ citation.filename }}</strong>
      <el-tag size="small">
        第 {{ citation.page }} 页
      </el-tag>
    </div>
    <p>{{ citation.text }}</p>
    <small>
      相关度 {{ citation.score.toFixed(3) }}
    </small>
  </el-card>
</template>

<style scoped>
.citation-card {
  margin-top: 10px;
  background: #f8fafc;
}

.citation-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

p {
  margin: 10px 0;
  line-height: 1.7;
}

small {
  color: #64748b;
}
</style>
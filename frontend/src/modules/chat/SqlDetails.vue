<script setup lang="ts">
defineProps<{
  sql: string;
  rowCount: number | null;
}>();
</script>

<template>
  <el-collapse class="sql-details">
    <el-collapse-item title="查看只读 SQL">
      <div class="sql-meta">
        返回行数：{{ rowCount ?? 0 }}
      </div>
      <pre><code>{{ sql }}</code></pre>
    </el-collapse-item>
  </el-collapse>
</template>

<style scoped>
.sql-details {
  margin-top: 12px;
}

.sql-meta {
  margin-bottom: 8px;
  color: #64748b;
}

pre {
  overflow-x: auto;
  margin: 0;
  padding: 14px;
  border-radius: 8px;
  color: #dbeafe;
  background: #0f172a;
}
</style>
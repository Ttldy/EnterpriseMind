<script setup lang="ts">
defineProps<{
  status: "PROCESSING" | "READY" | "FAILED";
  error: string | null;
}>();
</script>

<template>
  <div>
    <el-tag
      v-if="status === 'READY'"
      type="success"
    >
      可检索
    </el-tag>
    <el-tag
      v-else-if="status === 'PROCESSING'"
      type="warning"
    >
      处理中
    </el-tag>
    <el-tooltip
      v-else
      :content="error ?? '未知解析错误'"
    >
      <el-tag type="danger">
        解析失败
      </el-tag>
    </el-tooltip>
  </div>
</template>
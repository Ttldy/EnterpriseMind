<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { errorMessage } from "@/api/client";
import {
  createUser,
  fetchUserOptions,
  fetchUsers,
  updateUser,
} from "./api";
import type {
  UserOptions,
  UserRow,
} from "./api";

const users = ref<UserRow[]>([]);
const options = ref<UserOptions>({
  departments: [],
  roles: [],
});
const loading = ref(false);
const dialogVisible = ref(false);
const form = reactive({
  username: "",
  password: "",
  department_id: 0,
  role_ids: [] as number[],
});

async function load(): Promise<void> {
  loading.value = true;
  try {
    const [userRows, optionData] =
      await Promise.all([
        fetchUsers(),
        fetchUserOptions(),
      ]);
    users.value = userRows;
    options.value = optionData;
  } finally {
    loading.value = false;
  }
}

function openCreate(): void {
  form.username = "";
  form.password = "";
  form.department_id =
    options.value.departments[0]?.id ?? 0;
  form.role_ids = [];
  dialogVisible.value = true;
}

async function submitCreate(): Promise<void> {
  try {
    await createUser({ ...form });
    dialogVisible.value = false;
    ElMessage.success("用户创建成功");
    await load();
  } catch (error) {
    ElMessage.error(errorMessage(error));
  }
}

async function toggleActive(
  user: UserRow,
): Promise<void> {
  try {
    await updateUser(user.id, {
      is_active: !user.is_active,
    });
    await load();
  } catch (error) {
    ElMessage.error(errorMessage(error));
  }
}

async function changeRoles(
  user: UserRow,
  roleIds: number[],
): Promise<void> {
  try {
    await updateUser(user.id, {
      role_ids: roleIds,
    });
    await load();
  } catch (error) {
    ElMessage.error(errorMessage(error));
  }
}

onMounted(() => {
  void load();
});
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户与权限</h1>
        <p class="muted">
          管理账号、部门和固定角色
        </p>
      </div>
      <el-button type="primary" @click="openCreate">
        创建用户
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="users"
        row-key="id"
      >
        <el-table-column
          prop="username"
          label="用户名"
          width="180"
        />
        <el-table-column label="部门" width="150">
          <template #default="{ row }">
            {{ row.department.name }}
          </template>
        </el-table-column>
        <el-table-column label="角色" min-width="360">
          <template #default="{ row }">
            <el-select
              :model-value="
                row.roles.map(
                  (role: { id: number }) => role.id,
                )
              "
              multiple
              @change="
                changeRoles(
                  row,
                  $event as number[],
                )
              "
            >
              <el-option
                v-for="role in options.roles"
                :key="role.id"
                :label="role.name"
                :value="role.id"
              />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag
              :type="
                row.is_active
                  ? 'success'
                  : 'danger'
              "
            >
              {{ row.is_active ? "启用" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              text
              :type="
                row.is_active ? 'danger' : 'success'
              "
              @click="toggleActive(row)"
            >
              {{ row.is_active ? "禁用" : "启用" }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      title="创建用户"
      width="520px"
    >
      <el-form label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item label="部门">
          <el-select
            v-model="form.department_id"
            class="full-width"
          >
            <el-option
              v-for="item in options.departments"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="form.role_ids"
            multiple
            class="full-width"
          >
            <el-option
              v-for="item in options.roles"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="submitCreate"
        >
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.full-width {
  width: 100%;
}
</style>

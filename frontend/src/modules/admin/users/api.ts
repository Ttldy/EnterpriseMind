import { api } from "@/api/client";

export interface OptionItem {
  id: number;
  name: string;
}

export interface UserRow {
  id: number;
  username: string;
  department: OptionItem;
  roles: OptionItem[];
  is_active: boolean;
}

export interface UserOptions {
  departments: OptionItem[];
  roles: OptionItem[];
}

export interface UserCreatePayload {
  username: string;
  password: string;
  department_id: number;
  role_ids: number[];
}

export async function fetchUsers(): Promise<UserRow[]> {
  const response =
    await api.get<UserRow[]>("/admin/users");
  return response.data;
}

export async function fetchUserOptions(): Promise<
  UserOptions
> {
  const response =
    await api.get<UserOptions>(
      "/admin/users/options",
    );
  return response.data;
}

export async function createUser(
  payload: UserCreatePayload,
): Promise<UserRow> {
  const response = await api.post<UserRow>(
    "/admin/users",
    payload,
  );
  return response.data;
}

export async function updateUser(
  id: number,
  payload: {
    department_id?: number;
    role_ids?: number[];
    is_active?: boolean;
  },
): Promise<UserRow> {
  const response = await api.patch<UserRow>(
    `/admin/users/${id}`,
    payload,
  );
  return response.data;
}
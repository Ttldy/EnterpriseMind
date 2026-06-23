export interface CurrentUser {
  id: number;
  username: string;
  department: string;
  roles: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}
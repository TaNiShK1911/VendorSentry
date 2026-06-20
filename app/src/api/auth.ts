import client from './client';
import type { LoginRequest, LoginResponse, User } from '@/types';

export const authApi = {
  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await client.post<LoginResponse>('/auth/login', data);
    return response.data;
  },

  async getMe(): Promise<User> {
    const response = await client.get<User>('/auth/me');
    return response.data;
  },

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },

  getToken(): string | null {
    return localStorage.getItem('access_token');
  },

  getStoredUser(): User | null {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;
    try {
      return JSON.parse(userStr) as User;
    } catch {
      return null;
    }
  },

  storeAuth(response: LoginResponse): void {
    localStorage.setItem('access_token', response.access_token);
    // Ensure user has a 'name' field for display
    const user = response.user;
    if (!user.name && user.first_name) {
      user.name = `${user.first_name} ${user.last_name || ''}`.trim();
    }
    localStorage.setItem('user', JSON.stringify(user));
  },
};

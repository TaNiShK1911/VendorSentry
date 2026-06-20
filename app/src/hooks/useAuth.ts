import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/api';
import type { LoginRequest, LoginResponse } from '@/types';

export function useAuth() {
  const queryClient = useQueryClient();

  const {
    data: user,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      // Only try /me if we have a token
      const token = authApi.getToken();
      if (!token) return null;

      try {
        const userData = await authApi.getMe();
        return userData;
      } catch {
        // If /me fails (401, network error), fall back to stored user
        const storedUser = authApi.getStoredUser();
        if (!storedUser) {
          // No stored user and token is invalid — clear everything
          authApi.logout();
          return null;
        }
        return storedUser;
      }
    },
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (response: LoginResponse) => {
      authApi.storeAuth(response);
      queryClient.setQueryData(['auth', 'me'], response.user);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      authApi.logout();
    },
    onSuccess: () => {
      queryClient.clear();
      // Use hash-compatible redirect
      window.location.hash = '#/login';
      window.location.reload();
    },
  });

  const hasRole = useCallback(
    (roles: string[]): boolean => {
      if (!user) return false;
      return roles.includes(user.role);
    },
    [user]
  );

  const isCiso = user?.role === 'ciso';
  const isProcurement = user?.role === 'procurement';
  const isAuditor = user?.role === 'auditor';
  const canEdit = isCiso || isProcurement;
  const canDelete = isCiso;
  const canAcknowledge = isCiso || isProcurement;
  const canExtract = isCiso || isProcurement;
  const canViewEvaluation = isCiso;

  return {
    user: user || null,
    isLoading,
    error,
    isAuthenticated: !!user,
    login: loginMutation.mutateAsync,
    loginLoading: loginMutation.isPending,
    loginError: loginMutation.error,
    logout: logoutMutation.mutate,
    hasRole,
    isCiso,
    isProcurement,
    isAuditor,
    canEdit,
    canDelete,
    canAcknowledge,
    canExtract,
    canViewEvaluation,
  };
}

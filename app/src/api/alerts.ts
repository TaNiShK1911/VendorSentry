import client from './client';
import type {
  Alert,
  AlertListResponse,
  AlertSummary,
  AlertFilters,
} from '@/types';

export interface AlertListParams extends AlertFilters {
  page?: number;
  per_page?: number;
}

export const alertsApi = {
  async list(params: AlertListParams = {}): Promise<AlertListResponse> {
    const response = await client.get<AlertListResponse>('/alerts', { params });
    return response.data;
  },

  async getSummary(): Promise<AlertSummary> {
    const response = await client.get<AlertSummary>('/alerts/summary');
    return response.data;
  },

  async acknowledge(id: string): Promise<Alert> {
    const response = await client.post<Alert>(`/alerts/${id}/acknowledge`);
    return response.data;
  },

  async resolve(id: string): Promise<Alert> {
    const response = await client.post<Alert>(`/alerts/${id}/resolve`, {});
    return response.data;
  },

  async bulkAcknowledge(ids: string[]): Promise<void> {
    await client.post('/alerts/bulk/acknowledge', { ids });
  },

  async bulkResolve(ids: string[]): Promise<void> {
    await client.post('/alerts/bulk/resolve', { ids });
  },
};

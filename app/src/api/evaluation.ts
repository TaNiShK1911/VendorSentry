import client from './client';
import type { EvaluationMetrics } from '@/types';

export const evaluationApi = {
  async getMetrics(): Promise<EvaluationMetrics> {
    const response = await client.get<EvaluationMetrics>('/admin/evaluation');
    return response.data;
  },
};

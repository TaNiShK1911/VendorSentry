import client from './client';
import type {
  VendorScore,
  VendorCertifications,
  VendorBreaches,
  VendorEvidence,
  ScoreDistribution,
  ScoreTrend,
} from '@/types';

export const scoringApi = {
  async getVendorScore(vendorId: string): Promise<VendorScore> {
    const response = await client.get<VendorScore>(`/vendors/${vendorId}/score`);
    return response.data;
  },

  async getVendorCertifications(vendorId: string): Promise<VendorCertifications> {
    const response = await client.get<VendorCertifications>(`/vendors/${vendorId}/certifications`);
    return response.data;
  },

  async getVendorBreaches(vendorId: string): Promise<VendorBreaches> {
    const response = await client.get<VendorBreaches>(`/vendors/${vendorId}/breaches`);
    return response.data;
  },

  async getVendorEvidence(vendorId: string): Promise<VendorEvidence> {
    const response = await client.get<VendorEvidence>(`/vendors/${vendorId}/evidence`);
    return response.data;
  },

  async getScoreDistribution(): Promise<ScoreDistribution> {
    const response = await client.get<ScoreDistribution>('/portfolio/score-distribution');
    return response.data;
  },

  async getScoreTrend(range: string = '90d'): Promise<ScoreTrend> {
    const response = await client.get<ScoreTrend>('/portfolio/score-trend', {
      params: { range },
    });
    return response.data;
  },
};

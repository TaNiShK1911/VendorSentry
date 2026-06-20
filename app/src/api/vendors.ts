import client from './client';
import type {
  Vendor,
  VendorListResponse,
  VendorCreateRequest,
  VendorUpdateRequest,
  VendorFilters,
} from '@/types';

export interface VendorListParams extends VendorFilters {
  page?: number;
  per_page?: number;
  sort?: string;
}

export const vendorsApi = {
  async list(params: VendorListParams = {}): Promise<VendorListResponse> {
    const response = await client.get<VendorListResponse>('/vendors', { params });
    return response.data;
  },

  async getById(id: string): Promise<Vendor> {
    const response = await client.get<Vendor>(`/vendors/${id}`);
    return response.data;
  },

  async create(data: VendorCreateRequest): Promise<Vendor> {
    const response = await client.post<Vendor>('/vendors', data);
    return response.data;
  },

  async update(id: string, data: VendorUpdateRequest): Promise<Vendor> {
    const response = await client.patch<Vendor>(`/vendors/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await client.delete(`/vendors/${id}`);
  },

  async exportCsv(params: VendorFilters = {}): Promise<Blob> {
    const response = await client.get('/vendors/export.csv', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  async getReport(id: string, format: 'pdf' | 'json' = 'pdf'): Promise<Blob> {
    const response = await client.get(`/vendors/${id}/report`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },
};

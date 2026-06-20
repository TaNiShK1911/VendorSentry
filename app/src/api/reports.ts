import client from './client';

export const reportsApi = {
  async getVendorReport(vendorId: string, format: 'pdf' | 'json' | 'markdown' = 'pdf'): Promise<Blob | string> {
    const response = await client.get(`/vendors/${vendorId}/report`, {
      params: { format },
      responseType: format === 'markdown' ? 'text' : 'blob',
    });
    return response.data;
  },

  async getPortfolioReport(format: 'pdf' | 'json' | 'markdown' = 'pdf'): Promise<Blob | string> {
    const response = await client.get('/portfolio/report', {
      params: { format },
      responseType: format === 'markdown' ? 'text' : 'blob',
    });
    return response.data;
  },
};

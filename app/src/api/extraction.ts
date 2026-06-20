import client from './client';
import type { ExtractionJob, DocumentType } from '@/types';

export const extractionApi = {
  async startExtraction(
    vendorId: string,
    file: File,
    documentType: DocumentType
  ): Promise<ExtractionJob> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    const response = await client.post<ExtractionJob>(
      `/vendors/${vendorId}/extract`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  async getStatus(jobId: string): Promise<ExtractionJob> {
    const response = await client.get<ExtractionJob>(`/extraction-jobs/${jobId}`);
    return response.data;
  },
};

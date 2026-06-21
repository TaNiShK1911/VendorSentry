import apiClient from './client';

export interface DataSource {
  endpoint: string;
  summary: string;
}

export interface CopilotResponse {
  answer: string;
  data_used: DataSource[];
  follow_up_suggestions: string[];
  confidence: 'high' | 'partial' | 'none';
  no_data_reason: string | null;
}

export interface ConversationTurn {
  role: 'user' | 'assistant';
  content: string;
}

export const copilotApi = {
  query: async (query: string, conversationHistory: ConversationTurn[] = []): Promise<CopilotResponse> => {
    const response = await apiClient.post('/copilot/query', {
      query,
      conversation_history: conversationHistory,
    });
    return response.data;
  },
};

import { useState, useRef, useCallback } from 'react';
import { copilotApi, type CopilotResponse, type ConversationTurn } from '@/api/copilot';

export interface CopilotMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: CopilotResponse;
  isLoading?: boolean;
  error?: string;
}

export function useCopilot() {
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const historyRef = useRef<ConversationTurn[]>([]);

  const sendQuery = useCallback(async (query: string) => {
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    // Add user message
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: 'user', content: query },
      { id: assistantMsgId, role: 'assistant', content: '', isLoading: true },
    ]);
    setIsLoading(true);

    try {
      const response = await copilotApi.query(query, historyRef.current);

      // Update conversation history for multi-turn
      historyRef.current = [
        ...historyRef.current,
        { role: 'user', content: query },
        { role: 'assistant', content: response.answer },
      ];

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? { ...msg, content: response.answer, response, isLoading: false }
            : msg
        )
      );
    } catch (err: any) {
      const errorMsg =
        err?.response?.data?.detail || err?.message || 'An error occurred while querying the Copilot.';
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? { ...msg, content: '', error: errorMsg, isLoading: false }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    historyRef.current = [];
  }, []);

  const sendFollowUp = useCallback(
    (suggestion: string) => sendQuery(suggestion),
    [sendQuery]
  );

  return { messages, isLoading, sendQuery, sendFollowUp, clearMessages };
}

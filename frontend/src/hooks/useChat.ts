import { useState } from 'react';
import { useRef } from 'react';

export interface LeadData {
  business_segment: string | null;
  annual_usage_mwh: number | null;
  contract_status: string | null;
  months_to_expiry: number | null;
  building_age: number | null;
  has_current_provider: boolean | null;
  tier: string | null;
}


export const useChat = (
  setLeadData: React.Dispatch<React.SetStateAction<LeadData>>
) => {
  const sessionId = useRef(`session-${Date.now()}`);
  const [messages, setMessages] = useState<
    { role: string; content: string }[]
  >([]);
  const [isTyping, setIsTyping] = useState(false);

  const sendMessage = async (text: string) => {
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setIsTyping(true);
    
    
    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: sessionId.current,
        }),
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '' },
      ]);

      let accumulatedResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const events = chunk.split('\n\n');

        for (let event of events) {
          if (!event.startsWith('data:')) continue;
          const data = event.replace('data:', '').trim();
          if (!data) continue;

          if (data.startsWith('[METADATA]')) {
            try {
              const json = JSON.parse(data.replace('[METADATA]', ''));
              setLeadData(json);
            } catch (e) {
              console.error('Metadata parse error:', e);
            }
            continue;
          }

          accumulatedResponse += data;

          setMessages((prev) => {
            const updated = [...prev];
            if (updated.length > 0) {
              updated[updated.length - 1].content = accumulatedResponse;
            }
            return updated;
          });
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            'Connection error. Please check if the backend is running.',
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return { messages, sendMessage, isTyping };
};
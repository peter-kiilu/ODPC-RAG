
import { ChatRequest, ChatResponse, HealthStatus } from '../types';

// EDIT THIS BASE URL TO YOUR ACTUAL BACKEND LINK
const BASE_URL = 'http://localhost:8000'; 

export const apiService = {
  async sendMessage(message: string): Promise<ChatResponse> {
    const response = await fetch(`${BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to get a response from the legal guard dogs.');
    }

    return response.json();
  },

  async clearHistory(): Promise<void> {
    const response = await fetch(`${BASE_URL}/clear`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to wipe the memory. The bots still remember...');
    }
  },

  async checkHealth(): Promise<HealthStatus> {
    const response = await fetch(`${BASE_URL}/health`);
    if (!response.ok) throw new Error('Bot is feeling sick.');
    return response.json();
  }
};

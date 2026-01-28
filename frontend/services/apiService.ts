import { ChatResponse, HealthStatus } from '../types';

// EDIT THIS BASE URL TO YOUR ACTUAL BACKEND LINK
const BASE_URL = 'http://localhost:8000';

/* ============================
   ✅ NEW: Session ID handling
   - Persists until browser reload
   - Valid UUID v4
============================ */
const SESSION_ID_KEY = 'odpc_session_id';

function getSessionId(): string {
  let sessionId = sessionStorage.getItem(SESSION_ID_KEY);

  if (!sessionId) {
    sessionId = crypto.randomUUID(); // ✅ Valid UUID v4
    sessionStorage.setItem(SESSION_ID_KEY, sessionId);
  }

  return sessionId;
}

export const apiService = {
  async sendMessage(message: string): Promise<ChatResponse> {
    const session_id = getSessionId(); // ✅ NEW

    const response = await fetch(`${BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        message,
        session_id, // ✅ NEW: sent to backend
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || 'Failed to get a response from the legal guard dogs.'
      );
    }

    return response.json();
  },

  async clearHistory(): Promise<void> {
    const session_id = getSessionId(); // ✅ NEW (optional but recommended)

    const response = await fetch(`${BASE_URL}/clear`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ session_id }), // ✅ Keeps backend aligned
    });

    if (!response.ok) {
      throw new Error('Failed to wipe the memory. The bots still remember...');
    }
  },

  async checkHealth(): Promise<HealthStatus> {
    const response = await fetch(`${BASE_URL}/health`, {
      credentials: 'include',
    });

    if (!response.ok) throw new Error('Bot is feeling sick.');
    return response.json();
  },
};

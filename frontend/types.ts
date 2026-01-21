
export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  sources?: string[];
  tokensUsed?: number;
  isError?: boolean;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  response: string;
  sources: string[];
  tokens_used: number;
}

export interface HealthStatus {
  Status: string;
  indexed_chunks: number;
  config_valid: boolean;
}

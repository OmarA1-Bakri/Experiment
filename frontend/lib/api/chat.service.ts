import { env } from '@/src/config/env';

import { apiClient } from './client';

import type { ChatConversation, ChatMessage } from '@/types/api';

export interface CreateConversationRequest {
  title?: string;
  initial_message?: string;
}

export interface SendMessageRequest {
  content: string;
}

export interface EvidenceRecommendationRequest {
  framework: string;
}

export interface ComplianceAnalysisRequest {
  framework: string;
}

export type ChatWebSocketMessage = {
  type: 'message' | 'typing' | 'error' | 'connection';
  data: any;
};

class ChatService {
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private messageHandlers: ((message: ChatWebSocketMessage) => void)[] = [];

  /**
   * Get all chat conversations
   */
  async getConversations(params?: {
    page?: number;
    page_size?: number;
  }): Promise<{ items: ChatConversation[]; total: number }> {
    const response = await apiClient.get<{ items: ChatConversation[]; total: number }>(
      '/chat/conversations',
      { params }
    );
    return response.data;
  }

  /**
   * Get a specific conversation
   */
  async getConversation(id: string): Promise<{
    conversation: ChatConversation;
    messages: ChatMessage[];
  }> {
    const response = await apiClient.get<{
      conversation: ChatConversation;
      messages: ChatMessage[];
    }>(`/chat/conversations/${id}`);
    return response.data;
  }

  /**
   * Create a new conversation
   */
  async createConversation(data?: CreateConversationRequest): Promise<{
    conversation: ChatConversation;
    messages: ChatMessage[];
  }> {
    const response = await apiClient.post<{
      conversation: ChatConversation;
      messages: ChatMessage[];
    }>('/chat/conversations', data || {});
    return response.data;
  }

  /**
   * Send a message in a conversation
   */
  async sendMessage(conversationId: string, data: SendMessageRequest): Promise<ChatMessage> {
    const response = await apiClient.post<ChatMessage>(
      `/chat/conversations/${conversationId}/messages`,
      data
    );
    return response.data;
  }

  /**
   * Delete (archive) a conversation
   */
  async deleteConversation(id: string): Promise<void> {
    await apiClient.delete(`/chat/conversations/${id}`);
  }

  /**
   * Get evidence recommendations
   */
  async getEvidenceRecommendations(data: EvidenceRecommendationRequest): Promise<{
    recommendations: Array<{
      control_id: string;
      control_name: string;
      evidence_type: string;
      priority: string;
      description: string;
      automation_available: boolean;
    }>;
    total_recommendations: number;
  }> {
    const response = await apiClient.post<any>('/chat/evidence-recommendations', data);
    return response.data;
  }

  /**
   * Get compliance gap analysis
   */
  async getComplianceGapAnalysis(data: ComplianceAnalysisRequest): Promise<{
    framework: string;
    completion_percentage: number;
    critical_gaps: string[];
    recommendations: string[];
    estimated_effort_hours: number;
  }> {
    const response = await apiClient.post<any>('/chat/compliance-gap-analysis', data);
    return response.data;
  }

  /**
   * Get context-aware recommendations
   */
  async getContextAwareRecommendations(
    framework: string,
    contextType: 'comprehensive' | 'guidance' = 'comprehensive'
  ): Promise<any> {
    const response = await apiClient.post<any>('/chat/context-aware-recommendations', null, {
      params: { framework, context_type: contextType },
    });
    return response.data;
  }

  /**
   * Generate evidence collection workflow
   */
  async generateEvidenceCollectionWorkflow(
    framework: string,
    controlId?: string,
    workflowType: 'comprehensive' | 'quick' = 'comprehensive'
  ): Promise<any> {
    const response = await apiClient.post<any>('/chat/evidence-collection-workflow', null, {
      params: {
        framework,
        control_id: controlId,
        workflow_type: workflowType,
      },
    });
    return response.data;
  }

  /**
   * Generate customized policy via chat
   */
  async generateCustomizedPolicy(
    framework: string,
    policyType: string,
    customRequirements?: string[]
  ): Promise<any> {
    const response = await apiClient.post<any>('/chat/generate-policy', null, {
      params: {
        framework,
        policy_type: policyType,
        custom_requirements: customRequirements?.join(','),
      },
    });
    return response.data;
  }

  /**
   * Get smart compliance guidance
   */
  async getSmartComplianceGuidance(
    framework: string,
    guidanceType: 'getting_started' | 'next_steps' | 'optimization' = 'getting_started'
  ): Promise<any> {
    const response = await apiClient.get<any>('/chat/smart-compliance-guidance', {
      params: { framework, guidance_type: guidanceType },
    });
    return response.data;
  }

  /**
   * Get AI cache metrics
   */
  async getCacheMetrics(): Promise<any> {
    const response = await apiClient.get<any>('/chat/cache/metrics');
    return response.data;
  }

  /**
   * Clear AI cache
   */
  async clearCache(pattern: string = '*'): Promise<{
    cleared_entries: number;
    pattern: string;
    cleared_at: string;
  }> {
    const response = await apiClient.delete<any>('/chat/cache/clear', {
      params: { pattern },
    });
    return response.data;
  }

  /**
   * Get AI performance metrics
   */
  async getPerformanceMetrics(): Promise<any> {
    const response = await apiClient.get<any>('/chat/performance/metrics');
    return response.data;
  }

  /**
   * Get WebSocket URL for a conversation
   */
  getWebSocketUrl(conversationId: string): string {
    return `${env.NEXT_PUBLIC_WEBSOCKET_URL}/${conversationId}`;
  }

  /**
   * WebSocket connection for real-time chat
   */
  connectWebSocket(conversationId: string): void {
    const wsUrl = this.getWebSocketUrl(conversationId);
    this.connectWebSocketWithUrl(wsUrl);
  }

  /**
   * Connect WebSocket with custom URL (includes auth token)
   */
  connectWebSocketWithUrl(wsUrl: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.close();
    }

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.notifyHandlers({ type: 'connection', data: { status: 'connected' } });
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.notifyHandlers({ type: 'message', data: message });
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.notifyHandlers({ type: 'error', data: error });
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.notifyHandlers({ type: 'connection', data: { status: 'disconnected' } });
      
      // Attempt to reconnect after 3 seconds
      this.reconnectTimeout = setTimeout(() => {
        this.connectWebSocket(conversationId);
      }, 3000);
    };
  }

  /**
   * Send message via WebSocket
   */
  sendWebSocketMessage(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  /**
   * Add WebSocket message handler
   */
  addMessageHandler(handler: (message: ChatWebSocketMessage) => void): () => void {
    this.messageHandlers.push(handler);
    
    // Return cleanup function
    return () => {
      this.messageHandlers = this.messageHandlers.filter((h) => h !== handler);
    };
  }

  /**
   * Notify all message handlers
   */
  private notifyHandlers(message: ChatWebSocketMessage): void {
    this.messageHandlers.forEach((handler) => handler(message));
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.messageHandlers = [];
  }
}

export const chatService = new ChatService();
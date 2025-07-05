import { apiClient } from './client';

import type { Policy } from '@/types/api';
import type { UnknownRecord } from '@/types/common';

export interface GeneratePolicyRequest {
  framework_id: string;
  policy_type?: 'comprehensive' | 'basic' | 'custom';
  custom_requirements?: string[];
}

export interface UpdatePolicyStatusRequest {
  status: 'draft' | 'under_review' | 'approved' | 'active' | 'archived';
  approved?: boolean;
}

export interface RegeneratePolicySectionRequest {
  section_title: string;
  additional_context?: string;
}

class PolicyService {
  /**
   * Get all policies for the current user
   */
  async getPolicies(params?: {
    framework_id?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<{ policies: Policy[] }> {
    const response = await apiClient.get<{ policies: Policy[] }>('/policies', { params });
    return response.data;
  }

  /**
   * Get a specific policy by ID
   */
  async getPolicy(id: string): Promise<Policy> {
    const response = await apiClient.get<Policy>(`/policies/${id}`);
    return response.data;
  }

  /**
   * Generate a new policy using AI
   */
  async generatePolicy(data: GeneratePolicyRequest): Promise<Policy> {
    const response = await apiClient.post<Policy>('/policies/generate', data);
    return response.data;
  }

  /**
   * Update policy status
   */
  async updatePolicyStatus(id: string, data: UpdatePolicyStatusRequest): Promise<{
    id: string;
    status: string;
    approved: boolean;
  }> {
    const response = await apiClient.patch<{
      id: string;
      status: string;
      approved: boolean;
    }>(`/policies/${id}/status`, data);
    return response.data;
  }

  /**
   * Approve a policy
   */
  async approvePolicy(id: string): Promise<{
    message: string;
    policy_id: string;
  }> {
    const response = await apiClient.put<{
      message: string;
      policy_id: string;
    }>(`/policies/${id}/approve`);
    return response.data;
  }

  /**
   * Archive a policy
   */
  async archivePolicy(id: string): Promise<void> {
    await apiClient.put(`/policies/${id}/archive`);
  }

  /**
   * Regenerate a specific section of a policy
   */
  async regeneratePolicySection(
    id: string,
    data: RegeneratePolicySectionRequest
  ): Promise<Policy> {
    const response = await apiClient.post<Policy>(
      `/policies/${id}/regenerate-section`,
      data
    );
    return response.data;
  }

  /**
   * Export policy as PDF
   */
  async exportPolicyAsPDF(id: string): Promise<void> {
    await apiClient.download(`/policies/${id}/export/pdf`, `policy-${id}.pdf`);
  }

  /**
   * Export policy as Word document
   */
  async exportPolicyAsWord(id: string): Promise<void> {
    await apiClient.download(`/policies/${id}/export/word`, `policy-${id}.docx`);
  }

  /**
   * Get policy templates
   */
  async getPolicyTemplates(frameworkId?: string): Promise<{
    templates: Array<{
      id: string;
      name: string;
      description: string;
      framework: string;
      sections: string[];
    }>;
  }> {
    const params = frameworkId ? { framework_id: frameworkId } : undefined;
    const response = await apiClient.get<UnknownRecord>('/policies/templates', { params });
    return response.data;
  }

  /**
   * Clone a policy
   */
  async clonePolicy(id: string, newName: string): Promise<Policy> {
    const response = await apiClient.post<Policy>(`/policies/${id}/clone`, {
      name: newName,
    });
    return response.data;
  }

  /**
   * Get policy version history
   */
  async getPolicyVersionHistory(id: string): Promise<{
    versions: Array<{
      version: number;
      created_at: string;
      created_by: string;
      changes: string[];
    }>;
  }> {
    const response = await apiClient.get<UnknownRecord>(`/policies/${id}/versions`);
    return response.data;
  }
}

export const policyService = new PolicyService();
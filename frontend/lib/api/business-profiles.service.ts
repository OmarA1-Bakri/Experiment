import { BusinessProfileFieldMapper } from './business-profile/field-mapper';
import { apiClient } from './client';

import type { BusinessProfile } from '@/types/api';
import type { BusinessProfileFormData, FrameworkRecommendation } from '@/types/business-profile';

export interface CreateBusinessProfileRequest {
  company_name: string;
  industry: string;
  company_size: string;
  data_types: string[];
  storage_location: string;
  operates_in_uk: boolean;
  uk_data_subjects: boolean;
  regulatory_requirements: string[];
}

export interface UpdateBusinessProfileRequest extends Partial<CreateBusinessProfileRequest> {}

class BusinessProfileService {
  /**
   * Get all business profiles for the current user
   */
  async getBusinessProfiles(): Promise<BusinessProfile[]> {
    const response = await apiClient.get<any>('/business-profiles');
    // Handle both direct array and wrapped array responses
    const profileData = Array.isArray(response.data) ? response.data : response.data.data || [];
    // Transform each profile from API format to frontend format
    return profileData.map(profile => 
      BusinessProfileFieldMapper.transformAPIResponseForFrontend(profile)
    ).filter(Boolean) as BusinessProfile[];
  }

  /**
   * Get a specific business profile by ID
   */
  async getBusinessProfile(id: string): Promise<BusinessProfile> {
    const response = await apiClient.get<any>(`/business-profiles/${id}`);
    const transformed = BusinessProfileFieldMapper.transformAPIResponseForFrontend(response.data);
    if (!transformed) {
      throw new Error('Failed to transform business profile data');
    }
    return transformed;
  }

  /**
   * Create a new business profile
   */
  async createBusinessProfile(data: CreateBusinessProfileRequest): Promise<BusinessProfile> {
    // Transform data to API format before sending
    const apiData = BusinessProfileFieldMapper.transformFormDataForAPI(data);
    const response = await apiClient.post<any>('/business-profiles', apiData);
    
    // Transform response back to frontend format
    const transformed = BusinessProfileFieldMapper.transformAPIResponseForFrontend(response.data);
    if (!transformed) {
      throw new Error('Failed to transform business profile data');
    }
    return transformed;
  }

  /**
   * Update an existing business profile
   */
  async updateBusinessProfile(id: string, data: UpdateBusinessProfileRequest): Promise<BusinessProfile> {
    // Transform data to API format before sending
    const apiData = BusinessProfileFieldMapper.transformFormDataForAPI(data);
    const response = await apiClient.put<any>(`/business-profiles/${id}`, apiData);
    
    // Transform response back to frontend format
    const transformed = BusinessProfileFieldMapper.transformAPIResponseForFrontend(response.data);
    if (!transformed) {
      throw new Error('Failed to transform business profile data');
    }
    return transformed;
  }

  /**
   * Delete a business profile
   */
  async deleteBusinessProfile(id: string): Promise<void> {
    await apiClient.delete(`/business-profiles/${id}`);
  }

  /**
   * Get business profile compliance status
   */
  async getBusinessProfileCompliance(id: string): Promise<any> {
    const response = await apiClient.get<any>(`/business-profiles/${id}/compliance`);
    return response.data;
  }

  /**
   * Get the current user's business profile
   */
  async getProfile(): Promise<BusinessProfile | null> {
    try {
      const profiles = await this.getBusinessProfiles();
      return profiles.length > 0 ? profiles[0] : null;
    } catch (error) {
      console.error('Failed to get profile:', error);
      throw error;
    }
  }

  /**
   * Save a new profile or update existing one
   */
  async saveProfile(data: BusinessProfileFormData): Promise<BusinessProfile> {
    try {
      // Check if user already has a profile
      const existingProfile = await this.getProfile();
      
      if (existingProfile) {
        // Update existing profile
        return await this.updateProfile(existingProfile.id, data as any);
      } else {
        // Create new profile
        return await this.createBusinessProfile(data as any);
      }
    } catch (error) {
      console.error('Failed to save profile:', error);
      throw error;
    }
  }

  /**
   * Update profile with partial data
   */
  async updateProfile(profile: BusinessProfile, updates: Partial<BusinessProfileFormData>): Promise<BusinessProfile> {
    // Create update payload with only changed fields
    const updatePayload = BusinessProfileFieldMapper.createUpdatePayload(profile, updates);
    return await this.updateBusinessProfile(profile.id, updatePayload);
  }

  /**
   * Delete the current user's profile
   */
  async deleteProfile(): Promise<void> {
    try {
      const profile = await this.getProfile();
      if (profile) {
        await this.deleteBusinessProfile(profile.id);
      }
    } catch (error) {
      console.error('Failed to delete profile:', error);
      throw error;
    }
  }

  /**
   * Get framework recommendations based on profile
   */
  async getFrameworkRecommendations(): Promise<FrameworkRecommendation[]> {
    try {
      const response = await apiClient.get<FrameworkRecommendation[]>('/frameworks/recommendations');
      return response.data;
    } catch (error) {
      console.error('Failed to get framework recommendations:', error);
      // Return empty array if recommendations fail
      return [];
    }
  }
}

export const businessProfileService = new BusinessProfileService();
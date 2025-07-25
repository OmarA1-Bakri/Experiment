import { Shield, FileText, Heart, Banknote } from "lucide-react"

import { type Assessment } from "@/types/api"

export const frameworks = [
  {
    value: "GDPR",
    label: "GDPR", 
    icon: Shield,
  },
  {
    value: "ISO 27001",
    label: "ISO 27001",
    icon: FileText,
  },
  {
    value: "HIPAA",
    label: "HIPAA",
    icon: Heart,
  },
  {
    value: "FCA",
    label: "FCA",
    icon: Banknote,
  },
]

export const statuses = [
  {
    value: "completed",
    label: "Completed",
    color: "bg-success/20 text-success border-success/30",
    progressColor: "success",
  },
  {
    value: "in_progress",
    label: "In Progress", 
    color: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    progressColor: "info",
  },
  {
    value: "overdue",
    label: "Overdue",
    color: "bg-error/20 text-error border-error/30",
    progressColor: "error",
  },
  {
    value: "scheduled",
    label: "Scheduled",
    color: "bg-grey-600/20 text-grey-300 border-grey-600/30",
    progressColor: "warning",
  },
  {
    value: "under_review", 
    label: "Under Review",
    color: "bg-warning/20 text-warning border-warning/30",
    progressColor: "warning",
  },
]

// Re-export for compatibility
export type { Assessment }

export const sampleAssessments: Assessment[] = [
  {
    id: "ASM-001",
    title: "Q1 2024 GDPR Data Protection Audit",
    description: "Comprehensive GDPR compliance assessment",
    framework_id: "gdpr-001",
    framework_name: "GDPR",
    business_profile_id: "bp-001", 
    status: "overdue",
    progress: 75,
    score: 85,
    max_score: 100,
    started_at: "2024-03-01T00:00:00Z",
    created_at: "2024-03-15T00:00:00Z",
    updated_at: "2024-03-15T00:00:00Z",
    questions_count: 50,
    answered_count: 37,
  },
  {
    id: "ASM-002", 
    title: "Financial Reporting Compliance (Annual)",
    description: "Annual financial compliance review",
    framework_id: "fca-001",
    framework_name: "FCA",
    business_profile_id: "bp-001",
    status: "in_progress",
    progress: 45,
    score: 65,
    max_score: 100,
    started_at: "2024-04-01T00:00:00Z", 
    created_at: "2024-04-30T00:00:00Z",
    updated_at: "2024-04-30T00:00:00Z",
    questions_count: 40,
    answered_count: 18,
  },
  {
    id: "ASM-003",
    title: "Health & Safety Workplace Review", 
    description: "ISO 27001 security assessment",
    framework_id: "iso27001-001",
    framework_name: "ISO 27001",
    business_profile_id: "bp-001",
    status: "scheduled",
    progress: 0,
    created_at: "2024-05-10T00:00:00Z",
    updated_at: "2024-05-10T00:00:00Z",
    questions_count: 60,
    answered_count: 0,
  },
  {
    id: "ASM-004",
    title: "ISO 27001 Security Assessment",
    description: "Complete security framework assessment",
    framework_id: "iso27001-001", 
    framework_name: "ISO 27001",
    business_profile_id: "bp-001",
    status: "completed",
    progress: 100,
    score: 92,
    max_score: 100,
    started_at: "2024-02-01T00:00:00Z",
    completed_at: "2024-02-28T00:00:00Z",
    created_at: "2024-02-28T00:00:00Z",
    updated_at: "2024-02-28T00:00:00Z",
    questions_count: 55,
    answered_count: 55,
  },
  {
    id: "ASM-005",
    title: "Patient Data Privacy Check (HIPAA)",
    description: "HIPAA compliance verification",
    framework_id: "hipaa-001",
    framework_name: "HIPAA", 
    business_profile_id: "bp-001",
    status: "in_progress",
    progress: 62,
    score: 78,
    max_score: 100,
    started_at: "2024-05-01T00:00:00Z",
    created_at: "2024-05-28T00:00:00Z",
    updated_at: "2024-05-28T00:00:00Z", 
    questions_count: 45,
    answered_count: 28,
  },
  {
    id: "ASM-006",
    title: "Employee Training Compliance Verification",
    description: "GDPR training compliance check",
    framework_id: "gdpr-001",
    framework_name: "GDPR",
    business_profile_id: "bp-001", 
    status: "completed",
    progress: 100,
    score: 95,
    max_score: 100,
    started_at: "2024-03-10T00:00:00Z",
    completed_at: "2024-03-25T00:00:00Z",
    created_at: "2024-03-25T00:00:00Z",
    updated_at: "2024-03-25T00:00:00Z",
    questions_count: 30,
    answered_count: 30,
  },
]

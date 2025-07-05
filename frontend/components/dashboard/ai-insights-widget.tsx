"use client"


import {
  Brain,
  Lightbulb,
  AlertTriangle,
  TrendingUp,
  Bookmark,
  X,
  RefreshCw,
  ChevronRight,
  Sparkles
} from "lucide-react"
import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { dashboardService } from "@/lib/api/dashboard.service"
import { cn } from "@/lib/utils"

import type { DashboardInsight } from "@/lib/api/dashboard.service"
import type React from "react"

interface AIInsightsWidgetProps {
  insights: DashboardInsight[]
  className?: string
  maxInsights?: number
  isLoading?: boolean
  error?: string | null
  onRefresh?: () => void
  onDismiss?: (_insightId: string) => void
  onBookmark?: (_insightId: string) => void
  complianceProfile?: Record<string, unknown>
  onboardingData?: Record<string, unknown>
}

export function AIInsightsWidget({
  insights = [],
  className,
  maxInsights = 3,
  isLoading = false,
  error = null,
  onRefresh,
  onDismiss,
  onBookmark,
  complianceProfile,
  onboardingData
}: AIInsightsWidgetProps) {
  const [dismissedInsights, setDismissedInsights] = useState<Set<string>>(new Set())
  const [bookmarkedInsights, setBookmarkedInsights] = useState<Set<string>>(new Set())

  // Show loading state
  if (isLoading) {
    return <AIInsightsWidgetSkeleton />
  }

  // Show error state
  if (error) {
    return (
      <Card className={cn("border-destructive/50", className)}>
        <CardHeader>
          <CardTitle className="text-destructive">AI Insights Error</CardTitle>
          <CardDescription>{error}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={onRefresh} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </CardContent>
      </Card>
    )
  }

  const getInsightIcon = (type: DashboardInsight['type']) => {
    switch (type) {
      case 'tip':
        return <Lightbulb className="h-4 w-4 text-yellow-500" />
      case 'recommendation':
        return <TrendingUp className="h-4 w-4 text-blue-500" />
      case 'risk-alert':
        return <AlertTriangle className="h-4 w-4 text-red-500" />
      case 'optimization':
        return <Sparkles className="h-4 w-4 text-purple-500" />
      default:
        return <Brain className="h-4 w-4 text-muted-foreground" />
    }
  }

  const getInsightBadge = (type: DashboardInsight['type']) => {
    switch (type) {
      case 'tip':
        return <Badge variant="outline" className="text-yellow-600 border-yellow-200">Tip</Badge>
      case 'recommendation':
        return <Badge variant="outline" className="text-blue-600 border-blue-200">Recommendation</Badge>
      case 'risk-alert':
        return <Badge variant="outline" className="text-red-600 border-red-200">Risk Alert</Badge>
      case 'optimization':
        return <Badge variant="outline" className="text-purple-600 border-purple-200">Optimization</Badge>
      default:
        return <Badge variant="secondary">Insight</Badge>
    }
  }

  const getPriorityColor = (priority: number) => {
    if (priority >= 8) return 'border-l-red-500'
    if (priority >= 6) return 'border-l-amber-500'
    if (priority >= 4) return 'border-l-blue-500'
    return 'border-l-gray-500'
  }

  const handleDismiss = async (insightId: string) => {
    setDismissedInsights(prev => new Set([...prev, insightId]))
    if (onDismiss) {
      onDismiss(insightId)
    } else {
      try {
        await dashboardService.dismissInsight(insightId)
      } catch (error) {
        console.error('Failed to dismiss insight:', error)
      }
    }
  }

  const handleBookmark = async (insightId: string) => {
    setBookmarkedInsights(prev => {
      const newSet = new Set(prev)
      if (newSet.has(insightId)) {
        newSet.delete(insightId)
      } else {
        newSet.add(insightId)
      }
      return newSet
    })
    
    if (onBookmark) {
      onBookmark(insightId)
    } else {
      try {
        await dashboardService.bookmarkInsight(insightId)
      } catch (error) {
        console.error('Failed to bookmark insight:', error)
      }
    }
  }

  // Generate personalized insights based on compliance profile
  const generatePersonalizedInsights = () => {
    const personalizedInsights: DashboardInsight[] = []
    
    if (complianceProfile && insights.length === 0) {
      // Add insights based on priorities from onboarding
      if (complianceProfile.priorities?.includes("GDPR Compliance")) {
        personalizedInsights.push({
          id: "gdpr-start",
          type: "recommendation",
          title: "Start your GDPR compliance journey",
          description: "Based on your profile, GDPR is a top priority. Begin with a data mapping exercise.",
          priority: 9,
          created_at: new Date().toISOString(),
          dismissible: true,
          action: {
            label: "Start Data Mapping",
            route: "/assessments/new?framework=gdpr"
          }
        })
      }
      
      if (complianceProfile.maturityLevel === "beginner") {
        personalizedInsights.push({
          id: "policy-templates",
          type: "tip",
          title: "Use our AI-powered policy templates",
          description: "Save time with pre-built templates tailored to your industry.",
          priority: 8,
          created_at: new Date().toISOString(),
          dismissible: true,
          action: {
            label: "Browse Templates",
            route: "/policies/templates"
          }
        })
      }
      
      if (onboardingData?.timeline === "ASAP (< 1 month)") {
        personalizedInsights.push({
          id: "fast-track",
          type: "optimization",
          title: "Fast-track certification available",
          description: "Your timeline is urgent. Consider our accelerated compliance program.",
          priority: 10,
          created_at: new Date().toISOString(),
          dismissible: true,
          action: {
            label: "Learn More",
            route: "/fast-track"
          }
        })
      }
    }
    
    return [...personalizedInsights, ...insights]
  }

  const allInsights = generatePersonalizedInsights()
  
  const visibleInsights = allInsights
    .filter(insight => !dismissedInsights.has(insight.id))
    .sort((a, b) => {
      // Sort by priority first (higher priority first)
      const priorityDiff = b.priority - a.priority
      if (priorityDiff !== 0) return priorityDiff

      // Then by timestamp (newest first)
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
    .slice(0, maxInsights)

  return (
    <Card className={cn("border-0 shadow-sm hover:shadow-md transition-shadow duration-200", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-gold/10 flex items-center justify-center">
              <Brain className="h-5 w-5 text-gold" />
            </div>
            <div>
              <CardTitle className="text-xl font-bold text-navy">AI Insights</CardTitle>
              <CardDescription className="text-muted-foreground">
                Personalized compliance recommendations
              </CardDescription>
            </div>
          </div>
          {onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-2"
              onClick={onRefresh}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {visibleInsights.map((insight) => (
          <div
            key={insight.id}
            className={cn(
              "group rounded-lg border-l-4 bg-card p-4 transition-colors hover:bg-accent/50",
              getPriorityColor(insight.priority)
            )}
          >
            {/* Insight Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-start gap-3 flex-1">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 mt-0.5">
                  {getInsightIcon(insight.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-medium text-sm leading-tight">
                      {insight.title}
                    </h4>
                    {getInsightBadge(insight.type)}
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">
                    {insight.description}
                  </p>
                </div>
              </div>
              
              {insight.dismissible && (
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className={cn(
                      "h-auto p-1",
                      bookmarkedInsights.has(insight.id) ? "text-amber-500" : "text-muted-foreground"
                    )}
                    onClick={() => handleBookmark(insight.id)}
                  >
                    <Bookmark className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-1 text-muted-foreground hover:text-foreground"
                    onClick={() => handleDismiss(insight.id)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </div>

            {/* Action Button */}
            {insight.action && (
              <div className="mt-3">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto px-3 py-1.5 text-xs border"
                  onClick={() => window.location.href = insight.action!.route}
                >
                  {insight.action.label}
                  <ChevronRight className="h-3 w-3 ml-1" />
                </Button>
              </div>
            )}
          </div>
        ))}

        {visibleInsights.length === 0 && (
          <div className="text-center py-6 text-muted-foreground">
            <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No new insights</p>
            <p className="text-xs">Check back later for AI-powered recommendations</p>
          </div>
        )}

        {insights.length > maxInsights && (
          <div className="pt-2 border-t">
            <Button variant="ghost" size="sm" className="w-full">
              View All Insights ({insights.length})
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function AIInsightsWidgetSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Skeleton className="h-10 w-10 rounded-full" />
            <div>
              <Skeleton className="h-6 w-32 mb-1" />
              <Skeleton className="h-4 w-48" />
            </div>
          </div>
          <Skeleton className="h-8 w-8" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="border-l-4 border-gray-200 bg-card p-4">
            <div className="flex items-start gap-3">
              <Skeleton className="h-8 w-8 rounded-lg" />
              <div className="flex-1">
                <Skeleton className="h-4 w-3/4 mb-2" />
                <Skeleton className="h-3 w-full mb-1" />
                <Skeleton className="h-3 w-2/3" />
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

import type { LucideIcon } from "lucide-react"

interface StatsCardProps {
  title: string
  description: string
  value: string | number
  icon: LucideIcon
  trend?: {
    value: number
    isPositive: boolean
  }
  className?: string
}

export function StatsCard({ title, description, value, icon: Icon, trend, className }: StatsCardProps) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-foreground">{value}</div>
        <CardDescription className="text-muted-foreground">{description}</CardDescription>
        {trend && (
          <div className={`text-xs mt-1 ${trend.isPositive ? "text-success" : "text-error"}`}>
            {trend.isPositive ? "+" : ""}
            {trend.value}% from last month
          </div>
        )}
      </CardContent>
    </Card>
  )
}

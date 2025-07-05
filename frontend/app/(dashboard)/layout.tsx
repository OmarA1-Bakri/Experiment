import { CommandPalette } from "@/components/dashboard/command-palette"
import { KeyboardShortcutsDialog } from "@/components/dashboard/keyboard-shortcuts-dialog"
import { QuickActionsPanel } from "@/components/dashboard/quick-actions"
import { AppSidebar } from "@/components/navigation/app-sidebar"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

import type React from "react"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        {children}
        <QuickActionsPanel />
        <KeyboardShortcutsDialog />
        <CommandPalette />
      </SidebarInset>
    </SidebarProvider>
  )
}
"use client"

import * as React from "react"

import { AppSidebar } from "@/components/navigation/app-sidebar"
import { BreadcrumbNav } from "@/components/navigation/breadcrumb-nav"
import { GenerationProgress } from "@/components/policies/wizard/generation-progress"
import { SelectionCard } from "@/components/policies/wizard/selection-card"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { FormField } from "@/components/ui/form-field"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Stepper } from "@/components/ui/stepper"
import { Textarea } from "@/components/ui/textarea"
import { frameworks, policyTypes, companyDetails, scopeOptions } from "@/lib/data/policy-wizard-data"

const steps = ["Framework", "Policy Type", "Customize", "Generate"]

export default function NewPolicyPage() {
  const [currentStep, setCurrentStep] = React.useState(1)
  const [selectedFrameworks, setSelectedFrameworks] = React.useState<string[]>([])
  const [selectedPolicyType, setSelectedPolicyType] = React.useState<string | null>(null)

  const handleNext = () => setCurrentStep((prev) => Math.min(prev + 1, steps.length))
  const handleBack = () => setCurrentStep((prev) => Math.max(prev - 1, 1))

  const toggleFramework = (id: string) => {
    setSelectedFrameworks((prev) => (prev.includes(id) ? prev.filter((fwId) => fwId !== id) : [...prev, id]))
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 1: // Framework Selection
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {frameworks.map((fw) => (
              <SelectionCard
                key={fw.id}
                title={fw.name}
                description={fw.description}
                icon={fw.icon}
                isSelected={selectedFrameworks.includes(fw.id)}
                onClick={() => toggleFramework(fw.id)}
              />
            ))}
          </div>
        )
      case 2: // Policy Type Selection
        return (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {policyTypes.map((pt) => (
              <SelectionCard
                key={pt.id}
                title={pt.name}
                icon={pt.icon}
                isSelected={selectedPolicyType === pt.id}
                onClick={() => setSelectedPolicyType(pt.id)}
                className="aspect-square flex flex-col justify-center items-center text-center"
              />
            ))}
          </div>
        )
      case 3: // Customization Form
        return (
          <form className="space-y-8 max-w-3xl">
            <FormField label="Company Name" description="This will be used in the policy document.">
              <Input defaultValue={companyDetails.name} />
            </FormField>
            <div className="space-y-3">
              <Label>Policy Scope</Label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {scopeOptions.map((scope) => (
                  <div key={scope} className="flex items-center space-x-2">
                    <Checkbox id={`scope-${scope}`} />
                    <Label htmlFor={`scope-${scope}`} className="font-normal text-eggshell-white">
                      {scope}
                    </Label>
                  </div>
                ))}
              </div>
            </div>
            <FormField
              label="Additional Requirements"
              description="Specify any custom clauses or requirements you need to include."
            >
              <Textarea placeholder="e.g., All data must be stored within the EU." rows={5} />
            </FormField>
          </form>
        )
      case 4: // Generation Progress
        return (
          <div className="max-w-3xl mx-auto">
            <GenerationProgress />
          </div>
        )
      default:
        return null
    }
  }

  return (
    <div className="flex min-h-screen w-full">
      <AppSidebar />
      <main className="flex-1 flex flex-col p-6 lg:p-8 space-y-6">
        <BreadcrumbNav items={[{ title: "Policies", href: "/policies" }, { title: "New Policy" }]} />
        <div className="flex-1 flex flex-col w-full">
          <div className="space-y-2 mb-8 text-center">
            <h1 className="text-3xl font-bold text-eggshell-white">Policy Generation Wizard</h1>
            <p className="text-lg text-grey-600">Create a new compliance policy in just a few steps.</p>
          </div>

          <div className="mb-12">
            <Stepper steps={steps} currentStep={currentStep} />
          </div>

          <div className="flex-1">{renderStepContent()}</div>

          {currentStep < 4 && (
            <div className="flex justify-between mt-12 border-t border-white/10 pt-6">
              <Button variant="secondary" onClick={handleBack} disabled={currentStep === 1}>
                Back
              </Button>
              <Button
                variant="default"
                onClick={handleNext}
                disabled={
                  (currentStep === 1 && selectedFrameworks.length === 0) || (currentStep === 2 && !selectedPolicyType)
                }
              >
                {currentStep === 3 ? "Generate Policy" : "Next"}
              </Button>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

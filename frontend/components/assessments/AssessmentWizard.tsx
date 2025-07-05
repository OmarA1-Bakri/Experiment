"use client";


import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  Save,
  AlertCircle,
  CheckCircle,
  Clock
} from "lucide-react";
import { useState, useEffect, useCallback } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { 
  QuestionnaireEngine,
  type AssessmentFramework,
  type AssessmentContext,
  type AssessmentProgress,
  type AssessmentResult,
  type Question
} from "@/lib/assessment-engine";

import { AIErrorBoundary } from "./AIErrorBoundary";
import { AssessmentNavigation } from "./AssessmentNavigation";
import { FollowUpQuestion } from "./FollowUpQuestion";
import { ProgressTracker } from "./ProgressTracker";
import { QuestionRenderer } from "./QuestionRenderer";

import type React from "react"

interface AssessmentWizardProps {
  framework: AssessmentFramework;
  assessmentId: string;
  businessProfileId: string;
  onComplete: (_result: AssessmentResult) => void;
  onSave?: (_progress: AssessmentProgress) => void;
  onExit?: () => void;
}

export function AssessmentWizard({
  framework,
  assessmentId,
  businessProfileId,
  onComplete,
  onSave,
  onExit
}: AssessmentWizardProps) {
  const { toast } = useToast();
  const [engine, setEngine] = useState<QuestionnaireEngine | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [progress, setProgress] = useState<AssessmentProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isLoadingAI, setIsLoadingAI] = useState(false);

  // Initialize engine
  useEffect(() => {
    const context: AssessmentContext = {
      frameworkId: framework.id,
      assessmentId,
      businessProfileId,
      answers: new Map(),
      metadata: {}
    };

    const newEngine = new QuestionnaireEngine(framework, context, {
      autoSave: true,
      autoSaveInterval: 30,
      showProgress: true,
      enableNavigation: true,
      enableAI: true, // Enable AI follow-up questions
      useMockAIOnError: true, // Use mock questions if AI fails
      onProgress: (progress) => {
        setProgress(progress);
        if (onSave) {
          onSave(progress);
        }
      },
      onError: (error) => {
        setError(error.message);
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive"
        });
      }
    });

    // Try to load saved progress
    const hasProgress = newEngine.loadProgress();
    if (hasProgress) {
      toast({
        title: "Progress Restored",
        description: "Your previous progress has been loaded.",
      });
    }

    setEngine(newEngine);
    setCurrentQuestion(newEngine.getCurrentQuestion());
    setProgress(newEngine.getProgress());

    return () => {
      newEngine.destroy();
    };
  }, [framework, assessmentId, businessProfileId, onSave, toast]);

  const handleAnswer = useCallback((value: unknown) => {
    if (!engine || !currentQuestion) return;

    setValidationError(null);
    engine.answerQuestion(currentQuestion.id, value);
    setProgress(engine.getProgress());
  }, [engine, currentQuestion]);

  const handleNext = useCallback(async () => {
    if (!engine) return;

    setIsLoadingAI(true);
    try {
      const hasMore = await engine.nextQuestion();
      if (hasMore) {
        setCurrentQuestion(engine.getCurrentQuestion());
        setValidationError(null);
      } else {
        // Assessment complete - generate results with AI recommendations
        const result = await engine.calculateResults();
        onComplete(result);
      }
    } finally {
      setIsLoadingAI(false);
    }
  }, [engine, onComplete]);

  const handlePrevious = useCallback(() => {
    if (!engine) return;

    const hasPrevious = engine.previousQuestion();
    if (hasPrevious) {
      setCurrentQuestion(engine.getCurrentQuestion());
      setValidationError(null);
    }
  }, [engine]);

  const handleSaveProgress = useCallback(async () => {
    if (!engine || !progress) return;

    setIsSaving(true);
    try {
      // Save to backend (implement API call here)
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulated API call
      
      toast({
        title: "Progress Saved",
        description: "Your assessment progress has been saved.",
      });
    } catch {
      toast({
        title: "Save Failed",
        description: "Failed to save progress. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsSaving(false);
    }
  }, [engine, progress, toast]);

  const handleJumpToSection = useCallback((sectionIndex: number) => {
    if (!engine) return;

    const success = engine.jumpToSection(sectionIndex);
    if (success) {
      setCurrentQuestion(engine.getCurrentQuestion());
      setValidationError(null);
    }
  }, [engine]);

  if (!engine || !progress) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading assessment...</p>
        </div>
      </div>
    );
  }

  const currentSection = engine.getCurrentSection();
  const isLastQuestion = progress.answeredQuestions === progress.totalQuestions - 1;
  const isInAIMode = engine?.isInAIMode() || false;
  const currentAIQuestion = engine?.getCurrentAIQuestion();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy">{framework.name}</h1>
          <p className="text-muted-foreground">{framework.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSaveProgress}
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <Clock className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Progress
              </>
            )}
          </Button>
          {onExit && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onExit}
            >
              Exit
            </Button>
          )}
        </div>
      </div>

      {/* Progress Overview */}
      <ProgressTracker 
        progress={progress}
        framework={framework}
        onSectionClick={handleJumpToSection}
      />

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main Assessment Card */}
      <Card className="shadow-lg">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{currentSection?.title}</CardTitle>
              <CardDescription>{currentSection?.description}</CardDescription>
            </div>
            <div className="text-sm text-muted-foreground">
              Question {progress.answeredQuestions + 1} of {progress.totalQuestions}
            </div>
          </div>
          <Progress value={progress.percentComplete} className="mt-4" />
        </CardHeader>

        <CardContent>
          <AnimatePresence mode="wait">
            {isLoadingAI && (
              <motion.div
                key="loading-ai"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center py-12"
              >
                <div className="animate-pulse space-y-4 text-center">
                  <div className="h-12 w-12 rounded-full bg-primary/20 animate-pulse mx-auto" />
                  <p className="text-sm text-muted-foreground">
                    AI is analyzing your response and generating follow-up questions...
                  </p>
                </div>
              </motion.div>
            )}
            
            {!isLoadingAI && currentQuestion && (
              <motion.div
                key={currentQuestion.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
              >
                {isInAIMode && currentAIQuestion ? (
                  <AIErrorBoundary>
                    <FollowUpQuestion
                      question={currentAIQuestion}
                      value={engine.getAnswers().get(currentAIQuestion.id)?.value}
                      onChange={handleAnswer}
                      error={validationError}
                      frameworkId={framework.id}
                      {...(currentSection?.id && { sectionId: currentSection.id })}
                      userContext={{
                        ...(businessProfileId && { business_profile: { id: businessProfileId } }),
                        current_answers: Object.fromEntries(engine.getAnswers()),
                        assessment_progress: progress
                      }}
                      reasoning={currentAIQuestion.metadata?.['reasoning'] as string}
                    />
                  </AIErrorBoundary>
                ) : (
                  <QuestionRenderer
                    question={currentQuestion}
                    value={engine.getAnswers().get(currentQuestion.id)?.value}
                    onChange={handleAnswer}
                    error={validationError}
                    frameworkId={framework.id}
                    {...(currentSection?.id && { sectionId: currentSection.id })}
                    userContext={{
                      ...(businessProfileId && { business_profile: { id: businessProfileId } }),
                      current_answers: Object.fromEntries(engine.getAnswers()),
                      assessment_progress: progress
                    }}
                  />
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8">
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={isLoadingAI || (progress.answeredQuestions === 0 && !isInAIMode)}
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Previous
            </Button>

            <div className="flex items-center gap-2">
              {/* AI Mode Indicator */}
              {isInAIMode && (
                <div className="text-xs text-muted-foreground bg-primary/10 px-2 py-1 rounded">
                  AI Follow-up {engine?.getAIQuestionProgress()?.current || 1} of {engine?.getAIQuestionProgress()?.total || 1}
                </div>
              )}

              {currentQuestion?.validation?.required === false && !isInAIMode && (
                <Button
                  variant="ghost"
                  onClick={handleNext}
                >
                  Skip
                </Button>
              )}

              {/* AI questions can always be skipped */}
              {isInAIMode && (
                <Button
                  variant="ghost"
                  onClick={handleNext}
                >
                  Skip AI Question
                </Button>
              )}
              
              <Button
                onClick={handleNext}
                className="bg-gold hover:bg-gold-dark text-navy"
                disabled={isLoadingAI}
              >
                {isInAIMode ? (
                  engine?.hasAIQuestionsRemaining() ? (
                    <>
                      Next AI Question
                      <ChevronRight className="h-4 w-4 ml-2" />
                    </>
                  ) : (
                    <>
                      Continue Assessment
                      <ChevronRight className="h-4 w-4 ml-2" />
                    </>
                  )
                ) : isLastQuestion ? (
                  <>
                    Complete Assessment
                    <CheckCircle className="h-4 w-4 ml-2" />
                  </>
                ) : (
                  <>
                    Next
                    <ChevronRight className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Section Navigation */}
      <AssessmentNavigation
        framework={framework}
        currentSectionIndex={framework.sections.findIndex(s => s.id === currentSection?.id)}
        progress={progress}
        onSectionClick={handleJumpToSection}
      />
    </div>
  );
}
"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { TaskCreationState } from "@/types/task"
import { Step1DefineTask } from "./steps/step1-define-task"
import { Step2Subtasks } from "./steps/step2-subtasks"
import { Step3Metrics } from "./steps/step3-metrics"
import { Step4Matching } from "./steps/step4-matching"
import { Step5Allocation } from "./steps/step5-allocation"
import { Button } from "@/components/ui/button"
import { IconArrowLeft, IconX } from "@tabler/icons-react"
import { motion, AnimatePresence } from "motion/react"

interface TaskCreationModalProps {
  open: boolean
  onClose: () => void
  onComplete: (state: TaskCreationState) => void
}

export function TaskCreationModal({
  open,
  onClose,
  onComplete,
}: TaskCreationModalProps) {
  const [state, setState] = useState<TaskCreationState>({
    step: 1,
    task: {},
    generatedSubtasks: [],
    analyzedMetrics: [],
    matchResults: new Map(),
    finalAllocations: new Map(),
  })

  const handleNext = () => {
    if (state.step < 5) {
      setState({ ...state, step: (state.step + 1) as 1 | 2 | 3 | 4 | 5 })
    } else {
      onComplete(state)
      onClose()
    }
  }

  const handleBack = () => {
    if (state.step > 1) {
      setState({ ...state, step: (state.step - 1) as 1 | 2 | 3 | 4 | 5 })
    }
  }

  const updateState = (updates: Partial<TaskCreationState>) => {
    setState({ ...state, ...updates })
  }

  const stepTitles = [
    "Define Task",
    "Generate Subtasks",
    "Analyze Metrics",
    "Match Team Members",
    "Allocate & Deploy",
  ]

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl h-[90vh] p-0 gap-0" showCloseButton={false}>
        {/* Visually hidden title for accessibility */}
        <DialogTitle className="sr-only">
          {stepTitles[state.step - 1]} - Step {state.step} of 5
        </DialogTitle>

        {/* Header with step indicator */}
        <div className="border-b p-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {state.step > 1 && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleBack}
                className="shrink-0"
              >
                <IconArrowLeft className="size-5" />
              </Button>
            )}
            <div>
              <h2 className="text-2xl font-bold">
                {stepTitles[state.step - 1]}
              </h2>
              <p className="text-sm text-muted-foreground">
                Step {state.step} of 5
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <IconX className="size-5" />
          </Button>
        </div>

        {/* Progress bar */}
        <div className="h-1 bg-muted">
          <motion.div
            className="h-full bg-primary"
            initial={{ width: 0 }}
            animate={{ width: `${(state.step / 5) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>

        {/* Step content */}
        <div className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={state.step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              {state.step === 1 && (
                <Step1DefineTask state={state} updateState={updateState} />
              )}
              {state.step === 2 && (
                <Step2Subtasks state={state} updateState={updateState} />
              )}
              {state.step === 3 && (
                <Step3Metrics state={state} updateState={updateState} />
              )}
              {state.step === 4 && (
                <Step4Matching state={state} updateState={updateState} />
              )}
              {state.step === 5 && (
                <Step5Allocation state={state} updateState={updateState} />
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Footer with navigation */}
        <div className="border-t p-6 flex items-center justify-between">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleNext}>
            {state.step === 5 ? "Create Task" : "Next Step"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

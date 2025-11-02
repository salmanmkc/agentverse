"use client"

import { useState } from "react"
import { TaskCreationState, Subtask } from "@/types/task"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { IconLoader, IconSparkles, IconRefresh, IconChevronDown, IconChevronRight } from "@tabler/icons-react"
import { aiService } from "@/services/ai-service"
import { motion } from "motion/react"
import { Badge } from "@/components/ui/badge"

interface Step2SubtasksProps {
  state: TaskCreationState
  updateState: (updates: Partial<TaskCreationState>) => void
}

export function Step2Subtasks({ state, updateState }: Step2SubtasksProps) {
  const [isGenerating, setIsGenerating] = useState(false)
  const [expandedSubtasks, setExpandedSubtasks] = useState<Set<string>>(new Set())

  const handleGenerate = async () => {
    if (!state.task.title || !state.task.description) return

    setIsGenerating(true)
    try {
      const response = await aiService.generateSubtasks({
        title: state.task.title,
        description: state.task.description,
        context: state.task.tags?.join(", "),
      })

      updateState({
        generatedSubtasks: response.subtasks,
      })
    } catch (error) {
      console.error("Failed to generate subtasks:", error)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleBreakdownSubtask = async (subtask: Subtask) => {
    setIsGenerating(true)
    try {
      const response = await aiService.generateSubtasks({
        title: subtask.title,
        description: subtask.description,
      })

      // Add children to the subtask
      const updatedSubtasks = state.generatedSubtasks.map((st) =>
        st.id === subtask.id
          ? { ...st, children: response.subtasks }
          : st
      )

      updateState({ generatedSubtasks: updatedSubtasks })
      setExpandedSubtasks(new Set([...expandedSubtasks, subtask.id]))
    } catch (error) {
      console.error("Failed to break down subtask:", error)
    } finally {
      setIsGenerating(false)
    }
  }

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedSubtasks)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedSubtasks(newExpanded)
  }

  const hasSubtasks = state.generatedSubtasks.length > 0

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {!state.generatedSubtasks.length ? (
        <div className="text-center space-y-4 py-12">
          <div className="size-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
            <IconSparkles className="size-8 text-primary" />
          </div>
          <div>
            <h3 className="text-xl font-semibold mb-2">
              Ready to generate subtasks?
            </h3>
            <p className="text-muted-foreground max-w-md mx-auto">
              Our AI will analyze your task and create a breakdown of actionable
              subtasks. This usually takes a few seconds.
            </p>
          </div>
          <Button
            onClick={handleGenerate}
            disabled={isGenerating || !state.task.title || !state.task.description}
            size="lg"
            className="gap-2"
          >
            {isGenerating ? (
              <>
                <IconLoader className="size-5 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <IconSparkles className="size-5" />
                Generate Subtasks with AI
              </>
            )}
          </Button>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">
                Generated Subtasks ({state.generatedSubtasks.length})
              </h3>
              <p className="text-sm text-muted-foreground">
                Review and approve, or generate again
              </p>
            </div>
            <Button
              variant="outline"
              onClick={handleGenerate}
              disabled={isGenerating}
              className="gap-2"
            >
              <IconRefresh className="size-4" />
              Regenerate
            </Button>
          </div>

          <div className="space-y-3">
            {state.generatedSubtasks.map((subtask, index) => (
              <SubtaskCard
                key={subtask.id}
                subtask={subtask}
                index={index}
                isGenerating={isGenerating}
                isExpanded={expandedSubtasks.has(subtask.id)}
                onToggleExpand={() => toggleExpanded(subtask.id)}
                onBreakdown={handleBreakdownSubtask}
              />
            ))}
          </div>

          <div className="rounded-lg border bg-muted/30 p-4">
            <h4 className="font-medium mb-2">What happens next?</h4>
            <p className="text-sm text-muted-foreground">
              Once you approve these subtasks, we'll analyze key metrics to
              understand the importance and complexity of this task.
            </p>
          </div>
        </>
      )}
    </div>
  )
}

interface SubtaskCardProps {
  subtask: Subtask
  index: number
  isGenerating: boolean
  isExpanded: boolean
  onToggleExpand: () => void
  onBreakdown: (subtask: Subtask) => void
}

function SubtaskCard({
  subtask,
  index,
  isGenerating,
  isExpanded,
  onToggleExpand,
  onBreakdown,
}: SubtaskCardProps) {
  const hasChildren = subtask.children && subtask.children.length > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="outline">{index + 1}</Badge>
                <CardTitle className="text-base">{subtask.title}</CardTitle>
              </div>
              <p className="text-sm text-muted-foreground">
                {subtask.description}
              </p>
              {subtask.estimatedHours && (
                <p className="text-xs text-muted-foreground mt-2">
                  Estimated: ~{subtask.estimatedHours}h
                </p>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onBreakdown(subtask)}
              disabled={isGenerating}
              className="gap-2 shrink-0"
            >
              <IconSparkles className="size-4" />
              Break Down
            </Button>
          </div>
        </CardHeader>

        {hasChildren && (
          <>
            <div className="border-t px-6 py-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={onToggleExpand}
                className="gap-2 w-full justify-start"
              >
                {isExpanded ? (
                  <IconChevronDown className="size-4" />
                ) : (
                  <IconChevronRight className="size-4" />
                )}
                {subtask.children!.length} sub-subtasks
              </Button>
            </div>

            {isExpanded && (
              <CardContent className="bg-muted/30 space-y-2">
                {subtask.children!.map((child, childIndex) => (
                  <div
                    key={child.id}
                    className="flex items-start gap-3 p-3 rounded-lg border bg-card"
                  >
                    <Badge variant="secondary" className="shrink-0">
                      {index + 1}.{childIndex + 1}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <h5 className="font-medium text-sm">{child.title}</h5>
                      <p className="text-sm text-muted-foreground mt-1">
                        {child.description}
                      </p>
                      {child.estimatedHours && (
                        <p className="text-xs text-muted-foreground mt-1">
                          ~{child.estimatedHours}h
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            )}
          </>
        )}
      </Card>
    </motion.div>
  )
}

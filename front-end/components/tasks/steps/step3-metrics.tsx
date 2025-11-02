"use client"

import { useState, useEffect } from "react"
import { TaskCreationState } from "@/types/task"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { IconLoader, IconSparkles, IconAlertTriangle, IconTarget, IconClock, IconBrain, IconLink, IconShieldCheck } from "@tabler/icons-react"
import { aiService } from "@/services/ai-service"
import { motion } from "motion/react"
import { MetricRadarChart } from "@/components/visualizations/radar-chart"
import { Progress } from "@/components/ui/progress"

interface Step3MetricsProps {
  state: TaskCreationState
  updateState: (updates: Partial<TaskCreationState>) => void
}

const metricIcons = {
  impact: IconTarget,
  urgency: IconClock,
  complexity: IconBrain,
  dependencies: IconLink,
  risk: IconAlertTriangle,
}

const metricColors = {
  impact: "text-blue-500",
  urgency: "text-orange-500",
  complexity: "text-purple-500",
  dependencies: "text-green-500",
  risk: "text-red-500",
}

export function Step3Metrics({ state, updateState }: Step3MetricsProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisPhase, setAnalysisPhase] = useState<
    "identifying" | "calculating" | "validating" | "complete"
  >("identifying")

  useEffect(() => {
    if (state.analyzedMetrics.length === 0 && state.generatedSubtasks.length > 0) {
      handleAnalyze()
    }
  }, [])

  const handleAnalyze = async () => {
    if (!state.task.title || !state.task.description) return

    setIsAnalyzing(true)
    setAnalysisPhase("identifying")

    try {
      // Phase 1: Identifying metrics
      await new Promise((resolve) => setTimeout(resolve, 800))
      setAnalysisPhase("calculating")

      // Phase 2: Calculating
      await new Promise((resolve) => setTimeout(resolve, 800))
      setAnalysisPhase("validating")

      // Phase 3: Validating
      const response = await aiService.analyzeMetrics({
        title: state.task.title,
        description: state.task.description,
        subtasks: state.generatedSubtasks,
      })

      setAnalysisPhase("complete")
      await new Promise((resolve) => setTimeout(resolve, 500))

      updateState({
        analyzedMetrics: response.metrics,
      })
    } catch (error) {
      console.error("Failed to analyze metrics:", error)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const hasMetrics = state.analyzedMetrics.length > 0

  const phaseMessages = {
    identifying: "Identifying key metrics...",
    calculating: "Calculating metric values...",
    validating: "Validating analysis...",
    complete: "Analysis complete!",
  }

  const phaseProgress = {
    identifying: 25,
    calculating: 50,
    validating: 75,
    complete: 100,
  }

  if (isAnalyzing) {
    return (
      <div className="flex flex-col items-center justify-center space-y-6 py-12">
        <div className="size-20 bg-primary/10 rounded-full flex items-center justify-center">
          <IconSparkles className="size-10 text-primary animate-pulse" />
        </div>
        <div className="text-center space-y-2 max-w-md">
          <h3 className="text-xl font-semibold">Analyzing Task Metrics</h3>
          <p className="text-muted-foreground">
            {phaseMessages[analysisPhase]}
          </p>
        </div>
        <div className="w-full max-w-md space-y-2">
          <Progress value={phaseProgress[analysisPhase]} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Identifying</span>
            <span>Calculating</span>
            <span>Validating</span>
            <span>Complete</span>
          </div>
        </div>
      </div>
    )
  }

  if (!hasMetrics) {
    return (
      <div className="text-center space-y-4 py-12">
        <div className="size-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
          <IconSparkles className="size-8 text-primary" />
        </div>
        <div>
          <h3 className="text-xl font-semibold mb-2">Ready to analyze metrics?</h3>
          <p className="text-muted-foreground max-w-md mx-auto">
            We'll analyze your task to identify key metrics that define its
            importance, urgency, and complexity.
          </p>
        </div>
        <Button
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          size="lg"
          className="gap-2"
        >
          <IconSparkles className="size-5" />
          Analyze Metrics
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-full mx-auto">
      <div>
        <h3 className="text-lg font-semibold mb-2">Task Metrics Analysis</h3>
        <p className="text-sm text-muted-foreground">
          Understanding why this task matters and what it requires
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="text-base">Overall Score Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <MetricRadarChart metrics={state.analyzedMetrics} />
            </CardContent>
          </Card>
        </motion.div>

        {/* Metric Cards */}
        <div className="space-y-3">
          {state.analyzedMetrics.map((metric, index) => {
            const Icon = metricIcons[metric.category]
            const colorClass = metricColors[metric.category]

            return (
              <motion.div
                key={metric.metric}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-start gap-4">
                      <div className={`size-10 bg-muted rounded-lg flex items-center justify-center shrink-0`}>
                        <Icon className={`size-5 ${colorClass}`} />
                      </div>
                      <div className="flex-1 min-w-0 space-y-2">
                        <div className="flex items-center justify-between">
                          <h4 className="font-medium">{metric.metric}</h4>
                          <span className="text-lg font-semibold">{metric.value}</span>
                        </div>
                        <Progress value={metric.value} className="h-2" />
                        <p className="text-sm text-muted-foreground">
                          {metric.description}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </div>
      </div>

      <div className="rounded-lg border bg-muted/30 p-4">
        <h4 className="font-medium mb-2">What happens next?</h4>
        <p className="text-sm text-muted-foreground">
          We'll use these metrics to find the best team members for each subtask,
          matching skills, availability, and experience.
        </p>
      </div>
    </div>
  )
}

"use client"

import { useState, useEffect } from "react"
import { TaskCreationState } from "@/types/task"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { IconLoader, IconSparkles, IconCheck } from "@tabler/icons-react"
import { aiService } from "@/services/ai-service"
import { userService } from "@/services/user-service"
import { motion } from "motion/react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"

interface Step4MatchingProps {
  state: TaskCreationState
  updateState: (updates: Partial<TaskCreationState>) => void
}

export function Step4Matching({ state, updateState }: Step4MatchingProps) {
  const [isMatching, setIsMatching] = useState(false)
  const [matchingPhase, setMatchingPhase] = useState<
    "analyzing" | "comparing" | "ranking" | "complete"
  >("analyzing")
  const [currentSubtaskIndex, setCurrentSubtaskIndex] = useState(0)

  useEffect(() => {
    if (state.matchResults.size === 0 && state.generatedSubtasks.length > 0) {
      handleMatch()
    }
  }, [])

  const handleMatch = async () => {
    setIsMatching(true)
    const users = userService.getUsers()
    const results = new Map()

    for (let i = 0; i < state.generatedSubtasks.length; i++) {
      setCurrentSubtaskIndex(i)
      const subtask = state.generatedSubtasks[i]

      // Simulate phases
      setMatchingPhase("analyzing")
      await new Promise((resolve) => setTimeout(resolve, 600))

      setMatchingPhase("comparing")
      await new Promise((resolve) => setTimeout(resolve, 600))

      setMatchingPhase("ranking")
      const response = await aiService.findMatches({
        subtask,
        availableUserIds: users.map((u) => u.id),
      })

      results.set(subtask.id, response.matches)
      setMatchingPhase("complete")
      await new Promise((resolve) => setTimeout(resolve, 300))
    }

    updateState({ matchResults: results })
    setIsMatching(false)
  }

  const phaseMessages = {
    analyzing: "Analyzing team members...",
    comparing: "Comparing skills and experience...",
    ranking: "Ranking best matches...",
    complete: "Matching complete!",
  }

  const hasMatches = state.matchResults.size > 0

  if (isMatching) {
    const progress =
      ((currentSubtaskIndex + 1) / state.generatedSubtasks.length) * 100

    return (
      <div className="flex flex-col items-center justify-center space-y-6 py-12">
        <div className="size-20 bg-primary/10 rounded-full flex items-center justify-center relative">
          <IconSparkles className="size-10 text-primary animate-pulse" />
          <motion.div
            className="absolute inset-0 border-4 border-primary rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            style={{
              borderTopColor: "transparent",
              borderRightColor: "transparent",
            }}
          />
        </div>
        <div className="text-center space-y-2 max-w-md">
          <h3 className="text-xl font-semibold">Finding Best Matches</h3>
          <p className="text-muted-foreground">{phaseMessages[matchingPhase]}</p>
          <p className="text-sm text-muted-foreground">
            Subtask {currentSubtaskIndex + 1} of {state.generatedSubtasks.length}
          </p>
        </div>
        <div className="w-full max-w-md">
          <Progress value={progress} className="h-2" />
        </div>
      </div>
    )
  }

  if (!hasMatches) {
    return (
      <div className="text-center space-y-4 py-12">
        <div className="size-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
          <IconSparkles className="size-8 text-primary" />
        </div>
        <div>
          <h3 className="text-xl font-semibold mb-2">Ready to find matches?</h3>
          <p className="text-muted-foreground max-w-md mx-auto">
            We'll analyze your team and find the best person for each subtask based
            on skills, availability, and performance metrics.
          </p>
        </div>
        <Button
          onClick={handleMatch}
          disabled={isMatching}
          size="lg"
          className="gap-2"
        >
          <IconSparkles className="size-5" />
          Find Best Matches
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-full mx-auto">
      <div>
        <h3 className="text-lg font-semibold mb-2">Team Member Matching</h3>
        <p className="text-sm text-muted-foreground">
          Top 3 matches for each subtask. Select the best person for each role.
        </p>
      </div>

      <div className="space-y-6">
        {state.generatedSubtasks.map((subtask, index) => {
          const matches = state.matchResults.get(subtask.id) || []
          const selectedUser = state.finalAllocations.get(subtask.id)

          return (
            <motion.div
              key={subtask.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline">{index + 1}</Badge>
                      <h4 className="font-medium">{subtask.title}</h4>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {subtask.description}
                    </p>
                  </div>

                  <div className="space-y-2">
                    {matches.map((match) => {
                      const isSelected = selectedUser?.id === match.user.id
                      const isTopPick = match.rank === 1

                      return (
                        <motion.button
                          key={match.user.id}
                          onClick={() => {
                            const newAllocations = new Map(state.finalAllocations)
                            newAllocations.set(subtask.id, match.user)
                            updateState({ finalAllocations: newAllocations })
                          }}
                          className={`w-full text-left p-4 rounded-lg border transition-all ${
                            isSelected
                              ? "border-primary bg-primary/5 shadow-sm"
                              : isTopPick
                                ? "border-muted-foreground/30 hover:border-primary/50 hover:bg-accent/50"
                                : "border-muted-foreground/10 bg-muted/30 hover:border-muted-foreground/30"
                          }`}
                          whileHover={{ scale: 1.01 }}
                          whileTap={{ scale: 0.99 }}
                        >
                          <div className="flex items-center gap-4">
                            <Avatar className="size-12">
                              <AvatarImage
                                src={match.user.avatar}
                                alt={match.user.name}
                              />
                              <AvatarFallback>
                                {match.user.name
                                  .split(" ")
                                  .map((n) => n[0])
                                  .join("")}
                              </AvatarFallback>
                            </Avatar>

                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-medium">
                                  {match.user.name}
                                </span>
                                {isTopPick && (
                                  <Badge
                                    variant="default"
                                    className="text-xs bg-primary"
                                  >
                                    #1 Pick
                                  </Badge>
                                )}
                                {match.rank === 2 && (
                                  <Badge variant="secondary" className="text-xs">
                                    #2
                                  </Badge>
                                )}
                                {match.rank === 3 && (
                                  <Badge variant="outline" className="text-xs">
                                    #3
                                  </Badge>
                                )}
                              </div>
                              <p className="text-sm text-muted-foreground mb-2">
                                {match.reasoning}
                              </p>
                              <div className="flex items-center gap-2">
                                <div className="flex items-center gap-1">
                                  <span className="text-xs text-muted-foreground">
                                    Match:
                                  </span>
                                  <span className="text-xs font-medium">
                                    {match.matchPercentage}%
                                  </span>
                                </div>
                                {match.skillMatches.length > 0 && (
                                  <div className="flex gap-1">
                                    {match.skillMatches.slice(0, 3).map((skill) => (
                                      <Badge
                                        key={skill}
                                        variant="secondary"
                                        className="text-xs"
                                      >
                                        {skill}
                                      </Badge>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>

                            {isSelected && (
                              <div className="size-8 bg-primary rounded-full flex items-center justify-center shrink-0">
                                <IconCheck className="size-5 text-primary-foreground" />
                              </div>
                            )}
                          </div>
                        </motion.button>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      <div className="rounded-lg border bg-muted/30 p-4">
        <h4 className="font-medium mb-2">What happens next?</h4>
        <p className="text-sm text-muted-foreground">
          Review your selections and we'll create the task with all allocations,
          optionally pushing to GitHub and notifying team members.
        </p>
      </div>
    </div>
  )
}

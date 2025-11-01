"use client"

import { TaskCreationState } from "@/types/task"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { IconCheck, IconAlertCircle } from "@tabler/icons-react"
import { motion } from "motion/react"
import { useState } from "react"

interface Step5AllocationProps {
  state: TaskCreationState
  updateState: (updates: Partial<TaskCreationState>) => void
}

export function Step5Allocation({ state, updateState }: Step5AllocationProps) {
  const [createGitHubIssues, setCreateGitHubIssues] = useState(true)
  const [repository, setRepository] = useState("")
  const [projectBoard, setProjectBoard] = useState("")
  const [sendNotifications, setSendNotifications] = useState(true)

  const allocatedSubtasks = state.generatedSubtasks.filter((st) =>
    state.finalAllocations.has(st.id)
  )
  const unallocatedSubtasks = state.generatedSubtasks.filter(
    (st) => !state.finalAllocations.has(st.id)
  )

  const allAllocated = unallocatedSubtasks.length === 0

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h3 className="text-lg font-semibold mb-2">Review & Deploy</h3>
        <p className="text-sm text-muted-foreground">
          Review all allocations and configure deployment settings
        </p>
      </div>

      {/* Allocation Summary */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium">Allocation Summary</h4>
            {allAllocated ? (
              <Badge variant="default" className="gap-1 bg-green-500">
                <IconCheck className="size-3" />
                All Allocated
              </Badge>
            ) : (
              <Badge variant="secondary" className="gap-1">
                <IconAlertCircle className="size-3" />
                {unallocatedSubtasks.length} Unassigned
              </Badge>
            )}
          </div>

          <div className="space-y-3">
            {state.generatedSubtasks.map((subtask, index) => {
              const assignedUser = state.finalAllocations.get(subtask.id)

              return (
                <motion.div
                  key={subtask.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`flex items-center gap-4 p-3 rounded-lg border ${
                    assignedUser
                      ? "bg-card border-muted-foreground/20"
                      : "bg-muted/50 border-yellow-500/50"
                  }`}
                >
                  <Badge variant="outline" className="shrink-0">
                    {index + 1}
                  </Badge>

                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm line-clamp-1">
                      {subtask.title}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {subtask.estimatedHours && `~${subtask.estimatedHours}h`}
                    </p>
                  </div>

                  {assignedUser ? (
                    <div className="flex items-center gap-2 shrink-0">
                      <Avatar className="size-8">
                        <AvatarImage
                          src={assignedUser.avatar}
                          alt={assignedUser.name}
                        />
                        <AvatarFallback className="text-xs">
                          {assignedUser.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </AvatarFallback>
                      </Avatar>
                      <span className="text-sm font-medium">
                        {assignedUser.name}
                      </span>
                    </div>
                  ) : (
                    <Badge variant="outline" className="bg-yellow-500/10">
                      Unassigned
                    </Badge>
                  )}
                </motion.div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* GitHub Integration */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium mb-1">GitHub Integration</h4>
              <p className="text-sm text-muted-foreground">
                Automatically create issues and add to project board
              </p>
            </div>
            <Checkbox
              checked={createGitHubIssues}
              onCheckedChange={(checked) =>
                setCreateGitHubIssues(checked as boolean)
              }
            />
          </div>

          {createGitHubIssues && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="space-y-4 pt-4 border-t"
            >
              <div className="space-y-2">
                <Label htmlFor="repository">Repository</Label>
                <Input
                  id="repository"
                  placeholder="https://github.com/salmanmkc/agentverse"
                  value={repository}
                  onChange={(e) => setRepository(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  GitHub repository where issues will be created
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="project">Project Board (Optional)</Label>
                <Input
                  id="project"
                  placeholder="Project name or URL"
                  value={projectBoard}
                  onChange={(e) => setProjectBoard(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Add issues to an existing project board
                </p>
              </div>
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium mb-1">Team Notifications</h4>
              <p className="text-sm text-muted-foreground">
                Notify assigned team members via email
              </p>
            </div>
            <Checkbox
              checked={sendNotifications}
              onCheckedChange={(checked) =>
                setSendNotifications(checked as boolean)
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Warning for unallocated */}
      {!allAllocated && (
        <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-4 flex items-start gap-3">
          <IconAlertCircle className="size-5 text-yellow-600 dark:text-yellow-500 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-yellow-900 dark:text-yellow-100">
              Some subtasks are unassigned
            </h4>
            <p className="text-sm text-yellow-800 dark:text-yellow-200 mt-1">
              You can still create the task, but you'll need to assign these
              subtasks manually later. Consider going back to assign them now.
            </p>
          </div>
        </div>
      )}

      <div className="rounded-lg border bg-muted/30 p-4">
        <h4 className="font-medium mb-2">Ready to create?</h4>
        <p className="text-sm text-muted-foreground">
          Click "Create Task" to finalize. The task will be added to your
          dashboard{createGitHubIssues && ", GitHub issues will be created"}
          {sendNotifications && ", and team members will be notified"}.
        </p>
      </div>
    </div>
  )
}

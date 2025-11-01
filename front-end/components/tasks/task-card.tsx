"use client"

import { Task } from "@/types/task"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  IconChevronDown,
  IconChevronRight,
  IconCircleCheckFilled,
  IconClock,
} from "@tabler/icons-react"
import { useState } from "react"
import { SubtaskCard } from "./subtask-card"

interface TaskCardProps {
  task: Task
  onTaskClick?: (task: Task) => void
}

export function TaskCard({ task, onTaskClick }: TaskCardProps) {
  const [expanded, setExpanded] = useState(false)

  const priorityColors = {
    low: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
    medium: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400",
    high: "bg-red-500/10 text-red-700 dark:text-red-400",
  }

  const completedSubtasks = task.subtasks.filter(
    (st) => st.status === "completed"
  ).length

  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <CardTitle
                className="text-lg cursor-pointer hover:text-primary transition-colors"
                onClick={() => onTaskClick?.(task)}
              >
                {task.title}
              </CardTitle>
              <Badge
                variant="outline"
                className={priorityColors[task.priority]}
              >
                {task.priority}
              </Badge>
            </div>
            <CardDescription className="line-clamp-2">
              {task.description}
            </CardDescription>
          </div>
          {task.status === "closed" && (
            <IconCircleCheckFilled className="text-green-500 size-6 flex-shrink-0" />
          )}
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        <div className="space-y-3">
          {/* Progress */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-medium">{task.progress}%</span>
            </div>
            <Progress value={task.progress} className="h-2" />
          </div>

          {/* Subtasks Summary */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Subtasks</span>
            <span className="font-medium">
              {completedSubtasks} / {task.subtasks.length} completed
            </span>
          </div>

          {/* Assigned Members */}
          {task.assignedMembers.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Team:</span>
              <div className="flex -space-x-2">
                {task.assignedMembers.slice(0, 5).map((member) => (
                  <Avatar
                    key={member.id}
                    className="size-7 border-2 border-background"
                  >
                    <AvatarImage src={member.avatar} alt={member.name} />
                    <AvatarFallback className="text-xs">
                      {member.name
                        .split(" ")
                        .map((n) => n[0])
                        .join("")}
                    </AvatarFallback>
                  </Avatar>
                ))}
                {task.assignedMembers.length > 5 && (
                  <div className="size-7 rounded-full bg-muted border-2 border-background flex items-center justify-center text-xs">
                    +{task.assignedMembers.length - 5}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tags */}
          {task.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {task.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter className="pt-3 border-t flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <IconClock className="size-4" />
          <span>
            Updated {new Date(task.updatedAt).toLocaleDateString()}
          </span>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setExpanded(!expanded)}
          className="gap-1"
        >
          {expanded ? (
            <>
              <IconChevronDown className="size-4" />
              Hide subtasks
            </>
          ) : (
            <>
              <IconChevronRight className="size-4" />
              View subtasks
            </>
          )}
        </Button>
      </CardFooter>

      {/* Subtasks List */}
      {expanded && (
        <div className="border-t bg-muted/30 p-4 space-y-2">
          {task.subtasks.length > 0 ? (
            task.subtasks.map((subtask) => (
              <SubtaskCard key={subtask.id} subtask={subtask} />
            ))
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No subtasks yet
            </p>
          )}
        </div>
      )}
    </Card>
  )
}

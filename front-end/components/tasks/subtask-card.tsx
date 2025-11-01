"use client"

import { Subtask } from "@/types/task"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  IconCircleCheckFilled,
  IconLoader,
  IconCircle,
} from "@tabler/icons-react"

interface SubtaskCardProps {
  subtask: Subtask
}

export function SubtaskCard({ subtask }: SubtaskCardProps) {
  const statusConfig = {
    open: {
      icon: IconCircle,
      color: "text-muted-foreground",
      bgColor: "bg-muted",
      label: "Open",
    },
    in_progress: {
      icon: IconLoader,
      color: "text-blue-500",
      bgColor: "bg-blue-500/10",
      label: "In Progress",
    },
    completed: {
      icon: IconCircleCheckFilled,
      color: "text-green-500",
      bgColor: "bg-green-500/10",
      label: "Completed",
    },
  }

  const config = statusConfig[subtask.status]
  const StatusIcon = config.icon

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
      <StatusIcon className={`size-5 flex-shrink-0 mt-0.5 ${config.color}`} />

      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <h4 className="font-medium text-sm line-clamp-1">
              {subtask.title}
            </h4>
            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
              {subtask.description}
            </p>
          </div>
          <Badge variant="outline" className={`text-xs ${config.bgColor}`}>
            {config.label}
          </Badge>
        </div>

        <div className="flex items-center justify-between">
          {/* Assigned Users */}
          {subtask.assignedTo && subtask.assignedTo.length > 0 ? (
            <div className="flex items-center gap-2">
              <div className="flex -space-x-2">
                {subtask.assignedTo.map((user) => (
                  <Avatar
                    key={user.id}
                    className="size-6 border-2 border-background"
                  >
                    <AvatarImage src={user.avatar} alt={user.name} />
                    <AvatarFallback className="text-xs">
                      {user.name
                        .split(" ")
                        .map((n) => n[0])
                        .join("")}
                    </AvatarFallback>
                  </Avatar>
                ))}
              </div>
              <span className="text-xs text-muted-foreground">
                {subtask.assignedTo.map((u) => u.name).join(", ")}
              </span>
            </div>
          ) : (
            <span className="text-xs text-muted-foreground">Unassigned</span>
          )}

          {/* Estimated Hours */}
          {subtask.estimatedHours && (
            <span className="text-xs text-muted-foreground">
              ~{subtask.estimatedHours}h
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

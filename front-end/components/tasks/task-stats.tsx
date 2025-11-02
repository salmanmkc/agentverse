"use client"

import { Task } from "@/types/task"
import { User } from "@/types/user"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  IconTrendingUp,
  IconChecklist,
  IconUsers,
  IconAlertTriangle,
} from "@tabler/icons-react"

interface TaskStatsProps {
  tasks: Task[]
  users: User[]
}

export function TaskStats({ tasks, users }: TaskStatsProps) {
  const openTasks = tasks.filter((t) => t.status === "open")
  const closedTasks = tasks.filter((t) => t.status === "closed")
  const highPriorityTasks = openTasks.filter((t) => t.priority === "high")

  const totalSubtasks = openTasks.reduce(
    (sum, task) => sum + task.subtasks.length,
    0
  )
  const completedSubtasks = openTasks.reduce(
    (sum, task) =>
      sum + task.subtasks.filter((st) => st.status === "completed").length,
    0
  )
  const completionRate =
    totalSubtasks > 0
      ? Math.round((completedSubtasks / totalSubtasks) * 100)
      : 0

  const activeUsers = users.filter((u) => u.engagement.activeSubtasks > 0)

  return (
    <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Open Tasks</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {openTasks.length}
          </CardTitle>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            {closedTasks.length} completed this month
          </div>
          <div className="text-muted-foreground">
            {highPriorityTasks.length} high priority
          </div>
        </CardFooter>
      </Card>

      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Team Members</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {users.length}
          </CardTitle>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium items-center">
            <IconUsers className="size-4" />
            {activeUsers.length} currently active
          </div>
          <div className="text-muted-foreground">
            {users.length - activeUsers.length} available
          </div>
        </CardFooter>
      </Card>

      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Completion Rate</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {completionRate}%
          </CardTitle>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium items-center">
            {completionRate >= 70 ? (
              <>
                <IconTrendingUp className="size-4 text-green-500" />
                <span>On track</span>
              </>
            ) : (
              <>
                <IconAlertTriangle className="size-4 text-yellow-500" />
                <span>Needs attention</span>
              </>
            )}
          </div>
          <div className="text-muted-foreground">
            {completedSubtasks} of {totalSubtasks} subtasks done
          </div>
        </CardFooter>
      </Card>

      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Total Subtasks</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {totalSubtasks}
          </CardTitle>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium items-center">
            <IconChecklist className="size-4" />
            Across {openTasks.length} tasks
          </div>
          <div className="text-muted-foreground">
            {(totalSubtasks / openTasks.length).toFixed(1)} avg per task
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}

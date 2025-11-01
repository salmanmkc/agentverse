"use client"

import { useState } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { TaskStats } from "@/components/tasks/task-stats"
import { TaskCard } from "@/components/tasks/task-card"
import { UserCard } from "@/components/users/user-card"
import { TaskCreationModal } from "@/components/tasks/task-creation-modal"
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { IconPlus, IconChevronDown, IconChevronRight } from "@tabler/icons-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { taskService } from "@/services/task-service"
import { userService } from "@/services/user-service"
import { Task, TaskCreationState, Subtask } from "@/types/task"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { toast } from "sonner"

export default function Page() {
  const [tasks, setTasks] = useState(taskService.getTasks())
  const users = userService.getUsers()
  const [openTasks, setOpenTasks] = useState(taskService.getOpenTasks())
  const [closedTasks, setClosedTasks] = useState(taskService.getClosedTasks())
  const [showClosedTasks, setShowClosedTasks] = useState(false)
  const [showTaskModal, setShowTaskModal] = useState(false)

  const refreshTasks = () => {
    setTasks(taskService.getTasks())
    setOpenTasks(taskService.getOpenTasks())
    setClosedTasks(taskService.getClosedTasks())
  }

  const handleTaskClick = (task: Task) => {
    // TODO: Implement task details view
    console.log("Task clicked:", task)
  }

  const handleTaskCreationComplete = (state: TaskCreationState) => {
    // Create the task from the state
    const now = new Date().toISOString()

    // Flatten all subtasks including children
    const flattenSubtasks = (subtasks: Subtask[]): Subtask[] => {
      return subtasks.flatMap((st) => {
        const { children, ...subtaskWithoutChildren } = st
        const flattened = [subtaskWithoutChildren]
        if (children && children.length > 0) {
          flattened.push(...flattenSubtasks(children))
        }
        return flattened
      })
    }

    const allSubtasks = flattenSubtasks(state.generatedSubtasks)

    // Assign users to subtasks based on finalAllocations
    const subtasksWithAssignments = allSubtasks.map((st) => {
      const assignedUser = state.finalAllocations.get(st.id)
      return {
        ...st,
        assignedTo: assignedUser ? [assignedUser] : [],
      }
    })

    // Get all unique assigned members
    const assignedMembers = Array.from(
      new Set(
        Array.from(state.finalAllocations.values()).map((user) => user.id)
      )
    ).map((id) => users.find((u) => u.id === id)!)

    const newTask: Task = {
      id: `task-${Date.now()}`,
      title: state.task.title || "Untitled Task",
      description: state.task.description || "",
      status: state.task.status || "open",
      priority: state.task.priority || "medium",
      createdAt: now,
      updatedAt: now,
      progress: 0,
      tags: state.task.tags || [],
      subtasks: subtasksWithAssignments,
      metrics: state.analyzedMetrics,
      assignedMembers,
    }

    taskService.createTask(newTask)
    refreshTasks()

    toast.success("Task created successfully!", {
      description: `"${newTask.title}" has been added to your dashboard.`,
    })
  }

  return (
    <SidebarProvider
      className="w-full min-h-svh md:grid md:grid-cols-[minmax(0,var(--sidebar-width))_minmax(0,1fr)]"
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset className="min-w-0">
        <SiteHeader />
        <div className="@container/main flex flex-1 flex-col gap-2">
          <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
            {/* Stats */}
            <TaskStats tasks={tasks} users={users} />

            {/* Main Content Tabs */}
            <Tabs defaultValue="tasks" className="px-4 lg:px-6">
              <div className="flex items-center justify-between mb-4">
                <TabsList>
                  <TabsTrigger value="tasks">Tasks</TabsTrigger>
                  <TabsTrigger value="team">Team</TabsTrigger>
                </TabsList>

                <Button onClick={() => setShowTaskModal(true)} className="gap-2">
                  <IconPlus className="size-4" />
                  Create Task
                </Button>
              </div>

              <TabsContent value="tasks" className="space-y-4 mt-0">
                {/* Open Tasks */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">
                    Open Tasks ({openTasks.length})
                  </h3>
                  {openTasks.length > 0 ? (
                    <div className="grid grid-cols-1 gap-4 @4xl/main:grid-cols-2">
                      {openTasks.map((task) => (
                        <TaskCard
                          key={task.id}
                          task={task}
                          onTaskClick={handleTaskClick}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12 border rounded-lg bg-muted/30">
                      <p className="text-muted-foreground">
                        No open tasks. Create one to get started!
                      </p>
                    </div>
                  )}
                </div>

                {/* Closed Tasks */}
                {closedTasks.length > 0 && (
                  <Collapsible
                    open={showClosedTasks}
                    onOpenChange={setShowClosedTasks}
                  >
                    <CollapsibleTrigger asChild>
                      <Button
                        variant="ghost"
                        className="w-full justify-between p-4 h-auto"
                      >
                        <h3 className="text-lg font-semibold">
                          Closed Tasks ({closedTasks.length})
                        </h3>
                        {showClosedTasks ? (
                          <IconChevronDown className="size-5" />
                        ) : (
                          <IconChevronRight className="size-5" />
                        )}
                      </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="space-y-4 mt-4">
                      <div className="grid grid-cols-1 gap-4 @4xl/main:grid-cols-2">
                        {closedTasks.map((task) => (
                          <TaskCard
                            key={task.id}
                            task={task}
                            onTaskClick={handleTaskClick}
                          />
                        ))}
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                )}
              </TabsContent>

              <TabsContent value="team" className="space-y-4 mt-0">
                <h3 className="text-lg font-semibold">
                  Team Members ({users.length})
                </h3>
                <div className="grid grid-cols-1 gap-4 @2xl/main:grid-cols-2 @5xl/main:grid-cols-3">
                  {users.map((user) => (
                    <UserCard key={user.id} user={user} />
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </SidebarInset>

      {/* Task Creation Modal */}
      <TaskCreationModal
        open={showTaskModal}
        onClose={() => setShowTaskModal(false)}
        onComplete={handleTaskCreationComplete}
      />
    </SidebarProvider>
  )
}

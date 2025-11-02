"use client"

import { useState, useEffect } from "react"
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
  const [tasks, setTasks] = useState<Task[]>([])
  const [openTasks, setOpenTasks] = useState<Task[]>([])
  const [closedTasks, setClosedTasks] = useState<Task[]>([])
  const users = userService.getUsers()
  const [showClosedTasks, setShowClosedTasks] = useState(false)
  const [showTaskModal, setShowTaskModal] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const refreshTasks = async () => {
    try {
      const allTasks = await taskService.getTasks()
      const open = await taskService.getOpenTasks()
      const closed = await taskService.getClosedTasks()
      
      setTasks(allTasks)
      setOpenTasks(open)
      setClosedTasks(closed)
    } catch (error) {
      console.error("Failed to fetch tasks:", error)
      toast.error("Failed to load tasks")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refreshTasks()
  }, [])

  const handleTaskClick = (task: Task) => {
    // TODO: Implement task details view
    console.log("Task clicked:", task)
  }

  const handleTaskCreationComplete = async (state: TaskCreationState) => {
    // The task creation is now handled in the modal itself
    // This callback is just to refresh the tasks list after creation
    await refreshTasks()
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
                  {isLoading ? (
                    <div className="text-center py-12 border rounded-lg bg-muted/30">
                      <p className="text-muted-foreground">Loading tasks...</p>
                    </div>
                  ) : openTasks.length > 0 ? (
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

      {/* Floating Create Task Button */}
      <Button
        onClick={() => setShowTaskModal(true)}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg gap-2 z-50"
        size="icon"
      >
        <IconPlus className="size-6" />
        <span className="sr-only">Create Task</span>
      </Button>
    </SidebarProvider>
  )
}

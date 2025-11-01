import { Task, Subtask } from "@/types/task"
import { mockTasks } from "@/lib/mock-data"

class TaskService {
  private tasks: Task[] = [...mockTasks]

  getTasks(): Task[] {
    return this.tasks
  }

  getOpenTasks(): Task[] {
    return this.tasks.filter((t) => t.status === "open")
  }

  getClosedTasks(): Task[] {
    return this.tasks.filter((t) => t.status === "closed")
  }

  getTaskById(id: string): Task | undefined {
    return this.tasks.find((t) => t.id === id)
  }

  createTask(task: Task): void {
    this.tasks.unshift(task)
  }

  updateTask(id: string, updates: Partial<Task>): void {
    const index = this.tasks.findIndex((t) => t.id === id)
    if (index !== -1) {
      this.tasks[index] = { ...this.tasks[index], ...updates }
    }
  }

  deleteTask(id: string): void {
    this.tasks = this.tasks.filter((t) => t.id !== id)
  }

  updateSubtask(
    taskId: string,
    subtaskId: string,
    updates: Partial<Subtask>
  ): void {
    const task = this.getTaskById(taskId)
    if (!task) return

    const subtaskIndex = task.subtasks.findIndex((st) => st.id === subtaskId)
    if (subtaskIndex !== -1) {
      task.subtasks[subtaskIndex] = {
        ...task.subtasks[subtaskIndex],
        ...updates,
      }
      this.updateTask(taskId, task)
    }
  }

  calculateTaskProgress(task: Task): number {
    if (task.subtasks.length === 0) return 0

    const completedCount = task.subtasks.filter(
      (st) => st.status === "completed"
    ).length
    return Math.round((completedCount / task.subtasks.length) * 100)
  }
}

export const taskService = new TaskService()

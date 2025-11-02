import { Task, TaskCreationState, Subtask } from "@/types/task"

class TaskService {
  private apiBaseUrl = "/api/tasks"

  async getTasks(): Promise<Task[]> {
    const response = await fetch(this.apiBaseUrl)
    if (!response.ok) {
      throw new Error("Failed to fetch tasks")
    }
    return response.json()
  }
  
  async getOpenTasks(): Promise<Task[]> {
    const tasks = await this.getTasks()
    return tasks.filter((t) => t.status === "open")
  }

  async getClosedTasks(): Promise<Task[]> {
    const tasks = await this.getTasks()
    return tasks.filter((t) => t.status === "closed")
  }

  async getTaskById(id: string): Promise<Task | undefined> {
    const tasks = await this.getTasks()
    return tasks.find((task) => task.id === id)
  }

  async createTask(taskData: TaskCreationState): Promise<Task> {
    const response = await fetch(this.apiBaseUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(taskData),
    })

    if (!response.ok) {
      throw new Error("Failed to create task")
    }

    return response.json()
  }

  async updateTask(id: string, updates: Partial<Task>): Promise<Task | undefined> {
    const response = await fetch(`${this.apiBaseUrl}/${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    })

    if (!response.ok) {
      throw new Error("Failed to update task")
    }

    return response.json()
  }

  async deleteTask(id: string): Promise<void> {
    const response = await fetch(`${this.apiBaseUrl}/${id}`, {
      method: "DELETE",
    })

    if (!response.ok) {
      throw new Error("Failed to delete task")
    }
  }

  async updateSubtask(
    taskId: string,
    subtaskId: string,
    updates: Partial<Subtask>
  ): Promise<void> {
    const task = await this.getTaskById(taskId)
    if (!task) return

    const subtaskIndex = task.subtasks.findIndex((st) => st.id === subtaskId)
    if (subtaskIndex !== -1) {
      task.subtasks[subtaskIndex] = {
        ...task.subtasks[subtaskIndex],
        ...updates,
      }
      await this.updateTask(taskId, task)
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

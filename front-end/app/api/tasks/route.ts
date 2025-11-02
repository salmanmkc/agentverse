import { NextRequest, NextResponse } from "next/server"
import { TaskCreationState, Task } from "@/types/task"
import fs from "fs/promises"
import path from "path"

const tasksFilePath = path.join(process.cwd(), "app", "dashboard", "tasks.json")

async function getTasksFromFile(): Promise<Task[]> {
  try {
    const data = await fs.readFile(tasksFilePath, "utf-8")
    if (!data || data.trim() === "") {
      return []
    }
    return JSON.parse(data) as Task[]
  } catch (error) {
    // If the file doesn't exist or is empty, return an empty array
    return []
  }
}

async function saveTasksToFile(tasks: Task[]): Promise<void> {
  await fs.writeFile(tasksFilePath, JSON.stringify(tasks, null, 2))
}

export async function GET() {
  try {
    const tasks = await getTasksFromFile()
    return NextResponse.json(tasks)
  } catch (error) {
    console.error("Error fetching tasks:", error)
    return NextResponse.json(
      { message: "Error fetching tasks", error: (error as Error).message },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const taskData = (await request.json()) as TaskCreationState
    const tasks = await getTasksFromFile()
    
    const totalHours = taskData.generatedSubtasks.reduce(
      (sum, sub) => sum + (sub.estimatedHours || 0),
      0
    )

    // Calculate initial progress (0% since no subtasks are completed yet)
    const progress = taskData.generatedSubtasks.length > 0 ? 0 : 100

    // Extract assigned members from finalAllocations
    const assignedMemberIds = new Set(
      Array.from(taskData.finalAllocations.values()).map(user => user.id)
    )
    const assignedMembers = Array.from(assignedMemberIds).map(id => 
      taskData.finalAllocations.get(
        Array.from(taskData.finalAllocations.entries())
          .find(([_, user]) => user.id === id)?.[0] || ''
      )!
    ).filter(Boolean)

    const newTask: Task = {
      id: `task_${Date.now()}`,
      title: taskData.task.title!,
      description: taskData.task.description!,
      priority: taskData.task.priority!,
      status: "open",
      tags: taskData.task.tags || [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      progress,
      subtasks: taskData.generatedSubtasks.map((sub) => ({
        ...sub,
        completed: false,
        status: "todo"
      })),
      metrics: taskData.analyzedMetrics,
      allocations: taskData.finalAllocations,
      estimatedHours: totalHours,
      assignedMembers,
    }

    tasks.unshift(newTask)
    await saveTasksToFile(tasks)
    
    return NextResponse.json(newTask, { status: 201 })
  } catch (error) {
    console.error("Error creating task:", error)
    return NextResponse.json(
      { message: "Error creating task", error: (error as Error).message },
      { status: 500 }
    )
  }
}

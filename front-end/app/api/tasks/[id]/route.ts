import { NextRequest, NextResponse } from "next/server"
import { Task } from "@/types/task"
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
    return []
  }
}

async function saveTasksToFile(tasks: Task[]): Promise<void> {
  await fs.writeFile(tasksFilePath, JSON.stringify(tasks, null, 2))
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const updates = (await request.json()) as Partial<Task>
    const tasks = await getTasksFromFile()
    const taskIndex = tasks.findIndex((task) => task.id === params.id)

    if (taskIndex === -1) {
      return NextResponse.json({ message: "Task not found" }, { status: 404 })
    }

    const updatedTask = {
      ...tasks[taskIndex],
      ...updates,
      updatedAt: new Date().toISOString(),
    }
    tasks[taskIndex] = updatedTask
    await saveTasksToFile(tasks)

    return NextResponse.json(updatedTask)
  } catch (error) {
    console.error("Error updating task:", error)
    return NextResponse.json(
      { message: "Error updating task", error: (error as Error).message },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    let tasks = await getTasksFromFile()
    const taskIndex = tasks.findIndex((task) => task.id === params.id)

    if (taskIndex === -1) {
      return NextResponse.json({ message: "Task not found" }, { status: 404 })
    }

    tasks = tasks.filter((t) => t.id !== params.id)
    await saveTasksToFile(tasks)

    return NextResponse.json({ message: "Task deleted successfully" })
  } catch (error) {
    console.error("Error deleting task:", error)
    return NextResponse.json(
      { message: "Error deleting task", error: (error as Error).message },
      { status: 500 }
    )
  }
}

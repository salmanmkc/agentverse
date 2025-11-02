"use client"

import { TaskCreationState } from "@/types/task"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { IconX } from "@tabler/icons-react"
import { useState } from "react"

interface Step1DefineTaskProps {
  state: TaskCreationState
  updateState: (updates: Partial<TaskCreationState>) => void
}

export function Step1DefineTask({ state, updateState }: Step1DefineTaskProps) {
  const [tagInput, setTagInput] = useState("")

  const handleAddTag = () => {
    if (tagInput.trim() && (!state.task.tags || !state.task.tags.includes(tagInput.trim()))) {
      updateState({
        task: {
          ...state.task,
          tags: [...(state.task.tags || []), tagInput.trim()],
        },
      })
      setTagInput("")
    }
  }

  const handleRemoveTag = (tag: string) => {
    updateState({
      task: {
        ...state.task,
        tags: (state.task.tags || []).filter((t) => t !== tag),
      },
    })
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="space-y-2">
        <Label htmlFor="title">Task Title *</Label>
        <Input
          id="title"
          placeholder="e.g., Build User Authentication System"
          value={state.task.title || ""}
          onChange={(e) =>
            updateState({ task: { ...state.task, title: e.target.value } })
          }
        />
        <p className="text-sm text-muted-foreground">
          A clear, concise title for your task
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description *</Label>
        <Textarea
          id="description"
          placeholder="Describe the task in detail. What needs to be accomplished? What are the goals?"
          value={state.task.description || ""}
          onChange={(e) =>
            updateState({ task: { ...state.task, description: e.target.value } })
          }
          rows={6}
        />
        <p className="text-sm text-muted-foreground">
          Provide context and goals for the AI to generate relevant subtasks
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="priority">Priority</Label>
          <Select
            value={state.task.priority || "medium"}
            onValueChange={(value: "low" | "medium" | "high") =>
              updateState({ task: { ...state.task, priority: value } })
            }
          >
            <SelectTrigger id="priority">
              <SelectValue placeholder="Select priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="high">High</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="status">Status</Label>
          <Select
            value={state.task.status || "open"}
            onValueChange={(value: "open" | "closed") =>
              updateState({ task: { ...state.task, status: value } })
            }
          >
            <SelectTrigger id="status">
              <SelectValue placeholder="Select status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="tags">Tags</Label>
        <div className="flex gap-2">
          <Input
            id="tags"
            placeholder="Add tags (e.g., frontend, backend, security)"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault()
                handleAddTag()
              }
            }}
          />
          <Button type="button" variant="secondary" onClick={handleAddTag}>
            Add
          </Button>
        </div>
        {state.task.tags && state.task.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {state.task.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="gap-1">
                {tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="hover:bg-muted-foreground/20 rounded-full p-0.5"
                >
                  <IconX className="size-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-lg border bg-muted/30 p-4">
        <h4 className="font-medium mb-2">What happens next?</h4>
        <p className="text-sm text-muted-foreground">
          Our AI will analyze your task description and automatically generate
          relevant subtasks. You'll be able to review, edit, and even break down
          subtasks further before proceeding.
        </p>
      </div>
    </div>
  )
}

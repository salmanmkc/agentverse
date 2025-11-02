import { User } from "./user"

export interface Subtask {
  id: string
  title: string
  description: string
  status: "todo" | "in_progress" | "completed"
  assignedTo: User[]
  createdAt: string
  updatedAt: string
  matchCandidates?: MatchCandidate[]
  estimatedHours?: number
  children?: Subtask[] // For recursive breakdown
  completed: boolean
}

export interface MatchCandidate {
  user: User
  matchPercentage: number
  confidence: number // 0-100, confidence in this match
  rank: number // 1, 2, or 3
  reasoning: string
  skillMatches: string[]
  estimatedCompletionHours: number // How long this person would take
  githubActivity: {
    openPRs: number
    closedPRs: number
    openIssues: number
    closedIssues: number
  }
}

export interface TaskMetric {
  metric: string
  value: number // 0-100
  description: string
  category: "impact" | "urgency" | "complexity" | "dependencies" | "risk"
}

export interface Task {
  id: string
  title: string
  description: string
  status: "open" | "closed"
  priority: "low" | "medium" | "high"
  createdAt: string
  updatedAt: string
  progress?: number // 0-100
  tags: string[]
  subtasks: Subtask[]
  metrics: TaskMetric[]
  assignedMembers?: User[]
  githubIssueUrl?: string
  githubProjectUrl?: string
  allocations: Map<string, User>
  estimatedHours: number
}

export interface TaskCreationState {
  step: 1 | 2 | 3 | 4 | 5
  task: Partial<Task>
  generatedSubtasks: Subtask[]
  analyzedMetrics: TaskMetric[]
  matchResults: Map<string, MatchCandidate[]> // subtaskId -> candidates
  finalAllocations: Map<string, User> // subtaskId -> selected user
}

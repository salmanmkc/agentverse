import { Subtask, TaskMetric, MatchCandidate } from "./task"

// API Request Types
export interface GenerateSubtasksRequest {
  title: string
  description: string
  context?: string
}

export interface GenerateSubtasksResponse {
  subtasks: Subtask[]
}

export interface AnalyzeMetricsRequest {
  title: string
  description: string
  subtasks: Subtask[]
}

export interface AnalyzeMetricsResponse {
  metrics: TaskMetric[]
}

export interface FindMatchesRequest {
  subtask: Subtask
  availableUserIds?: string[]
}

export interface FindMatchesResponse {
  matches: MatchCandidate[]
}

export interface CreateGitHubIssuesRequest {
  taskTitle: string
  subtasks: Array<{
    subtaskId: string
    assignedUserId: string
  }>
  repository?: string
  projectBoard?: string
}

export interface CreateGitHubIssuesResponse {
  issueUrls: string[]
  projectUrl?: string
}

// API Client Config
export interface APIConfig {
  baseURL: string
  useMock: boolean
  timeout?: number
}

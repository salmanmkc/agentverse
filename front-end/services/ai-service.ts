import { features } from "@/config/features"
import { Subtask, TaskMetric, MatchCandidate } from "@/types/task"
import {
  GenerateSubtasksRequest,
  GenerateSubtasksResponse,
  AnalyzeMetricsRequest,
  AnalyzeMetricsResponse,
  FindMatchesRequest,
  FindMatchesResponse,
  CreateGitHubIssuesRequest,
  CreateGitHubIssuesResponse,
} from "@/types/api"
import { apiClient } from "./api-client"
import { mockUsers } from "@/lib/mock-data"

/**
 * AI Service - Handles all AI-powered features
 *
 * BACKEND INTEGRATION:
 * To connect to real AI backend:
 * 1. Set NEXT_PUBLIC_USE_REAL_AI=true in .env
 * 2. Set NEXT_PUBLIC_API_URL to your backend URL
 * 3. Ensure backend implements these endpoints:
 *    - POST /tasks/generate-subtasks
 *    - POST /tasks/analyze-metrics
 *    - POST /matching/find-candidates
 *    - POST /github/create-issues
 */
class AIService {
  private useMock = !features.USE_REAL_AI

  /**
   * Generate subtasks from task description
   * API Endpoint: POST /tasks/generate-subtasks
   */
  async generateSubtasks(
    request: GenerateSubtasksRequest
  ): Promise<GenerateSubtasksResponse> {
    if (this.useMock) {
      return this.mockGenerateSubtasks(request)
    }

    return apiClient.post<GenerateSubtasksResponse>(
      "/tasks/generate-subtasks",
      request
    )
  }

  /**
   * Analyze task metrics
   * API Endpoint: POST /tasks/analyze-metrics
   */
  async analyzeMetrics(
    request: AnalyzeMetricsRequest
  ): Promise<AnalyzeMetricsResponse> {
    if (this.useMock) {
      return this.mockAnalyzeMetrics(request)
    }

    return apiClient.post<AnalyzeMetricsResponse>(
      "/tasks/analyze-metrics",
      request
    )
  }

  /**
   * Find user matches for subtask
   * API Endpoint: POST /matching/find-candidates
   */
  async findMatches(
    request: FindMatchesRequest
  ): Promise<FindMatchesResponse> {
    if (this.useMock) {
      return this.mockFindMatches(request)
    }

    return apiClient.post<FindMatchesResponse>("/matching/find-candidates", request)
  }

  /**
   * Create GitHub issues for subtasks
   * API Endpoint: POST /github/create-issues
   */
  async createGitHubIssues(
    request: CreateGitHubIssuesRequest
  ): Promise<CreateGitHubIssuesResponse> {
    if (this.useMock) {
      return this.mockCreateGitHubIssues(request)
    }

    return apiClient.post<CreateGitHubIssuesResponse>(
      "/github/create-issues",
      request
    )
  }

  // ============ MOCK IMPLEMENTATIONS ============

  private async mockGenerateSubtasks(
    request: GenerateSubtasksRequest
  ): Promise<GenerateSubtasksResponse> {
    // Simulate API delay
    await this.delay(features.MOCK_DELAY_MS)

    const subtasks: Subtask[] = [
      {
        id: `st-${Date.now()}-1`,
        title: `Research and planning for ${request.title}`,
        description: `Conduct initial research and create detailed plan for implementing ${request.title}. Identify requirements and potential challenges.`,
        status: "open",
        assignedTo: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        estimatedHours: 8,
      },
      {
        id: `st-${Date.now()}-2`,
        title: `Core implementation`,
        description: `Implement the main functionality described in: ${request.description}`,
        status: "open",
        assignedTo: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        estimatedHours: 20,
      },
      {
        id: `st-${Date.now()}-3`,
        title: `Testing and quality assurance`,
        description: `Write comprehensive tests and perform QA to ensure quality of ${request.title}`,
        status: "open",
        assignedTo: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        estimatedHours: 12,
      },
      {
        id: `st-${Date.now()}-4`,
        title: `Documentation and deployment`,
        description: `Create documentation and deploy ${request.title} to production environment`,
        status: "open",
        assignedTo: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        estimatedHours: 6,
      },
    ]

    return { subtasks }
  }

  private async mockAnalyzeMetrics(
    request: AnalyzeMetricsRequest
  ): Promise<AnalyzeMetricsResponse> {
    await this.delay(features.MOCK_DELAY_MS + 500)

    // Generate semi-random but consistent metrics
    const hash = this.simpleHash(request.title)
    const metrics: TaskMetric[] = [
      {
        metric: "Impact",
        value: 60 + (hash % 35),
        description: `This task will significantly affect the system and users`,
        category: "impact",
      },
      {
        metric: "Urgency",
        value: 50 + ((hash * 2) % 40),
        description: `Time sensitivity based on project timeline`,
        category: "urgency",
      },
      {
        metric: "Complexity",
        value: 55 + ((hash * 3) % 40),
        description: `Technical complexity and skill requirements`,
        category: "complexity",
      },
      {
        metric: "Dependencies",
        value: 40 + ((hash * 4) % 50),
        description: `Number of other tasks and systems this affects`,
        category: "dependencies",
      },
      {
        metric: "Risk",
        value: 45 + ((hash * 5) % 40),
        description: `Potential risks and uncertainty involved`,
        category: "risk",
      },
    ]

    return { metrics }
  }

  private async mockFindMatches(
    request: FindMatchesRequest
  ): Promise<FindMatchesResponse> {
    await this.delay(features.MOCK_DELAY_MS + 800)

    // Simple matching algorithm for mock
    const availableUsers = mockUsers
    const subtaskLower = `${request.subtask.title} ${request.subtask.description}`.toLowerCase()

    // Calculate match scores
    const scoredUsers = availableUsers.map((user) => {
      let score = 50 // Base score

      // Check if user skills match subtask keywords
      user.skills.forEach((skill) => {
        if (subtaskLower.includes(skill.toLowerCase())) {
          score += 15
        }
      })

      // Factor in engagement metrics
      score += Math.min(user.engagement.completedTasks / 10, 10)
      score -= user.engagement.activeSubtasks * 3 // Penalize busy users
      score += Math.max(0, (5 - user.engagement.avgResponseTime) * 2)

      // Add some randomness to make it interesting
      score += Math.random() * 10 - 5

      return { user, score: Math.min(100, Math.max(0, score)) }
    })

    // Sort by score and take top 3
    scoredUsers.sort((a, b) => b.score - a.score)
    const top3 = scoredUsers.slice(0, 3)

    const matches: MatchCandidate[] = top3.map((item, index) => ({
      user: item.user,
      matchPercentage: Math.round(item.score),
      rank: (index + 1) as 1 | 2 | 3,
      reasoning: this.generateReasoning(item.user, request.subtask, item.score),
      skillMatches: item.user.skills.filter((skill) =>
        subtaskLower.includes(skill.toLowerCase())
      ),
    }))

    return { matches }
  }

  private async mockCreateGitHubIssues(
    request: CreateGitHubIssuesRequest
  ): Promise<CreateGitHubIssuesResponse> {
    await this.delay(features.MOCK_DELAY_MS)

    const issueUrls = request.subtasks.map(
      (st, idx) =>
        `https://github.com/example/repo/issues/${1000 + idx}` // Mock URLs
    )

    const projectUrl = request.projectBoard
      ? `https://github.com/example/repo/projects/${Math.floor(Math.random() * 10) + 1}`
      : undefined

    return { issueUrls, projectUrl }
  }

  // ============ HELPER METHODS ============

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  private simpleHash(str: string): number {
    let hash = 0
    for (let i = 0; i < str.length; i++) {
      hash = (hash << 5) - hash + str.charCodeAt(i)
      hash = hash & hash
    }
    return Math.abs(hash)
  }

  private generateReasoning(
    user: any,
    subtask: Subtask,
    score: number
  ): string {
    const reasons = []

    if (score > 80) {
      reasons.push(`${user.name} has excellent relevant experience`)
    } else if (score > 65) {
      reasons.push(`${user.name} has good relevant skills`)
    } else {
      reasons.push(`${user.name} has some relevant experience`)
    }

    if (user.engagement.activeSubtasks < 3) {
      reasons.push("currently has capacity")
    }

    if (user.engagement.avgResponseTime < 3) {
      reasons.push("responds quickly")
    }

    return reasons.join(" and ")
  }
}

export const aiService = new AIService()

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

  constructor() {
    console.log('AIService initialized:', {
      useMock: this.useMock,
      USE_REAL_AI: features.USE_REAL_AI,
      API_BASE_URL: features.API_BASE_URL,
    })
  }

  /**
   * Send streaming message to MCP backend
   * API Endpoint: POST http://localhost:8000
   */
  async sendStreamingMessage(
    text: string,
    onChunk?: (chunk: string) => void
  ): Promise<string> {
    try {
      const response = await fetch('http://localhost:8000', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          id: `test-${Date.now()}`,
          method: 'message/stream',
          params: {
            message: {
              role: 'user',
              parts: [
                {
                  kind: 'text',
                  text: text,
                },
              ],
              messageId: `msg-${Date.now()}`,
            },
          },
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullResponse = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          fullResponse += chunk
          
          if (onChunk) {
            onChunk(chunk)
          }
        }
      }

      return fullResponse
    } catch (error) {
      console.error('Streaming API call failed:', error)
      throw error
    }
  }

  /**
   * Generate subtasks from task description
   * API Endpoint: POST /tasks/generate-subtasks
   */
  async generateSubtasks(
    request: GenerateSubtasksRequest
  ): Promise<GenerateSubtasksResponse> {
    console.log('generateSubtasks called:', { useMock: this.useMock, request })
    
    if (this.useMock) {
      console.log('Using mock data for subtasks')
      return this.mockGenerateSubtasks(request)
    }

    console.log('Calling platform-engineer-p2p for subtasks')
    
    // Call the AI platform engineering backend using streaming API
    const prompt = `Generate subtasks for the following task:

Title: ${request.title}
Description: ${request.description}

Please provide a JSON response in this exact format:
{
  "subtasks": [
    {
      "id": "unique-id",
      "title": "Clear, concise title",
      "description": "Detailed description of what needs to be done",
      "status": "todo",
      "assignedTo": [],
      "createdAt": "ISO timestamp",
      "updatedAt": "ISO timestamp",
      "estimatedHours": 8,
      "completed": false
    }
  ]
}

Generate 4-6 subtasks that break down this task into actionable items. Each subtask should have:
- A unique id (format: "st-timestamp-index")
- A clear, concise title (no markdown formatting)
- A detailed description (no markdown formatting, no "Description:" prefix)
- estimatedHours based on complexity (realistic estimate)
- status: "todo"
- completed: false
- assignedTo: []
- Current ISO timestamps for createdAt and updatedAt

Return ONLY the JSON object, no additional text or markdown.`

    try {
      const fullResponse = await this.sendStreamingMessage(prompt)
      
      // Parse the AI response and format it as GenerateSubtasksResponse
      return this.parseSubtasksFromStream(fullResponse, request)
    } catch (error) {
      console.error("Failed to call AI backend:", error)
      // Fallback to mock data on error
      return this.mockGenerateSubtasks(request)
    }
  }

  private async parseSubtasksFromStream(
    fullResponse: string,
    request: GenerateSubtasksRequest
  ): Promise<GenerateSubtasksResponse> {
    try {
      console.log("Parsing AI response:", fullResponse)

      // Parse SSE (Server-Sent Events) format
      const lines = fullResponse.split('\n')
      let contentText = ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonData = JSON.parse(line.substring(6))
            
            // Extract text from the response - the artifact is directly in result, not in an array
            if (jsonData.result?.artifact) {
              const artifact = jsonData.result.artifact
              if (artifact.parts) {
                for (const part of artifact.parts) {
                  if (part.kind === 'text' && part.text) {
                    contentText += part.text
                  }
                }
              }
            }
          } catch (e) {
            // Skip lines that aren't valid JSON
            continue
          }
        }
      }

      console.log("Extracted content:", contentText)

      // Try to parse as JSON if it looks like JSON
      if (contentText.includes("{") && contentText.includes("subtasks")) {
        try {
          // Find the JSON object by counting braces to find the complete object
          const firstBrace = contentText.indexOf('{')
          
          if (firstBrace !== -1) {
            let braceCount = 0
            let inString = false
            let escapeNext = false
            let jsonEnd = -1
            
            for (let i = firstBrace; i < contentText.length; i++) {
              const char = contentText[i]
              
              if (escapeNext) {
                escapeNext = false
                continue
              }
              
              if (char === '\\') {
                escapeNext = true
                continue
              }
              
              if (char === '"' && !escapeNext) {
                inString = !inString
                continue
              }
              
              if (!inString) {
                if (char === '{') {
                  braceCount++
                } else if (char === '}') {
                  braceCount--
                  if (braceCount === 0) {
                    jsonEnd = i
                    break
                  }
                }
              }
            }
            
            if (jsonEnd !== -1) {
              const jsonStr = contentText.substring(firstBrace, jsonEnd + 1)
              console.log("Attempting to parse JSON:", jsonStr.substring(0, 100) + "...")
              const parsed = JSON.parse(jsonStr)
              
              if (parsed.subtasks && Array.isArray(parsed.subtasks)) {
                console.log("Successfully parsed JSON response with", parsed.subtasks.length, "subtasks")
                return parsed
              }
            }
          }
        } catch (jsonError) {
          console.warn("Failed to parse as JSON, falling back to text parsing:", jsonError)
        }
      }

      // Parse the natural language response into subtasks
      const subtasks: Subtask[] = []
      const textLines = contentText.split('\n').filter((l) => l.trim())
      
      let currentSubtask: Partial<Subtask> | null = null

      const baseTimestamp = Date.now()
      
      // Helper function to clean markdown formatting
      const cleanMarkdown = (text: string): string => {
        return text
          .replace(/\*\*/g, '') // Remove bold **
          .replace(/\*/g, '')   // Remove italics *
          .replace(/^-\s*/, '') // Remove leading dash
          .replace(/^Description:\s*/i, '') // Remove "Description:" prefix
          .trim()
      }
      
      for (let i = 0; i < textLines.length; i++) {
        const line = textLines[i].trim()
        
        // Look for numbered items like "1.", "2.", "1)", etc.
        const numberMatch = line.match(/^(\d+)[.)]\s*(.+)/)
        if (numberMatch) {
          // Save previous subtask if exists
          if (currentSubtask && currentSubtask.title) {
            subtasks.push({
              id: `st-${baseTimestamp}-${subtasks.length}`,
              title: cleanMarkdown(currentSubtask.title),
              description: cleanMarkdown(currentSubtask.description || currentSubtask.title),
              status: "todo",
              assignedTo: [],
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              estimatedHours: currentSubtask.estimatedHours || 8,
              completed: false,
            })
          }
          
          // Start new subtask - clean the title immediately
          currentSubtask = {
            title: numberMatch[2].trim(),
            estimatedHours: 8,
          }
        } else if (currentSubtask && line) {
          // Check for hour estimates
          const hourMatch = line.match(/(\d+)\s*(?:hours?|hrs?|h)/i)
          if (hourMatch) {
            currentSubtask.estimatedHours = parseInt(hourMatch[1])
          } else if (!currentSubtask.description) {
            // This line is part of the description
            currentSubtask.description = line
          } else {
            // Append to description
            currentSubtask.description += ' ' + line
          }
        }
      }

      // Add the last subtask
      if (currentSubtask && currentSubtask.title) {
        subtasks.push({
          id: `st-${baseTimestamp}-${subtasks.length}`,
          title: cleanMarkdown(currentSubtask.title),
          description: cleanMarkdown(currentSubtask.description || currentSubtask.title),
          status: "todo",
          assignedTo: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          estimatedHours: currentSubtask.estimatedHours || 8,
          completed: false,
        })
      }

      if (subtasks.length > 0) {
        console.log("Generated subtasks:", subtasks)
        return { subtasks }
      }

      console.warn("No subtasks found in response, using mock data")
      // Fallback to mock data if no subtasks found
      return await this.mockGenerateSubtasks(request)
    } catch (error) {
      console.error("Failed to parse AI response:", error)
      // Fallback to mock data if parsing fails
      return await this.mockGenerateSubtasks(request)
    }
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
        status: "todo",
        assignedTo: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        estimatedHours: 8,
        completed: false,
      },
      {
        id: `st-${Date.now()}-2`,
        title: `Core implementation`,
        description: `Implement the main functionality described in: ${request.description}`,
        status: "todo",
        assignedTo: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        estimatedHours: 20,
        completed: false,
      },
      {
        id: `st-${Date.now()}-3`,
        title: `Testing and quality assurance`,
        description: `Write comprehensive tests and perform QA to ensure quality of ${request.title}`,
        status: "todo",
        assignedTo: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        estimatedHours: 12,
        completed: false,
      },
      {
        id: `st-${Date.now()}-4`,
        title: `Documentation and deployment`,
        description: `Create documentation and deploy ${request.title} to production environment`,
        status: "todo",
        assignedTo: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        estimatedHours: 6,
        completed: false,
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

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

IMPORTANT: Respond with ONLY a valid JSON object in this exact format (no markdown, no code blocks, no additional text):

{
  "subtasks": [
    {
      "id": "st-${Date.now()}-1",
      "title": "Clear, concise title",
      "description": "Detailed description",
      "status": "todo",
      "assignedTo": [],
      "createdAt": "${new Date().toISOString()}",
      "updatedAt": "${new Date().toISOString()}",
      "estimatedHours": 8,
      "completed": false
    }
  ]
}

Generate 4-6 subtasks. Each subtask must include all fields above. Use realistic hour estimates based on complexity.`

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
      console.log("Parsing AI response, length:", fullResponse.length)
      console.log("Response preview:", fullResponse.substring(0, 300))

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

      console.log("Extracted content length:", contentText.length)
      console.log("Extracted content:", contentText)

      // Try to extract and parse JSON from the content
      // The AI might return JSON wrapped in markdown code blocks or with extra text
      let jsonStr = contentText.trim()
      
      // Remove markdown code blocks if present
      if (jsonStr.includes('```')) {
        const codeBlockMatch = jsonStr.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/)
        if (codeBlockMatch) {
          jsonStr = codeBlockMatch[1]
          console.log("Extracted JSON from markdown code block")
        }
      }
      
      // Try to find JSON object in the text
      if (jsonStr.includes("{") && jsonStr.includes("subtasks")) {
        try {
          // Find the first occurrence of { followed by "subtasks"
          let startIndex = jsonStr.indexOf('{')
          
          // Try each occurrence of { until we find valid JSON
          while (startIndex !== -1 && startIndex < jsonStr.length) {
            let braceCount = 0
            let inString = false
            let escapeNext = false
            let jsonEnd = -1
            
            for (let i = startIndex; i < jsonStr.length; i++) {
              const char = jsonStr[i]
              
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
              const candidateJson = jsonStr.substring(startIndex, jsonEnd + 1)
              console.log("Attempting to parse JSON candidate, length:", candidateJson.length)
              
              try {
                const parsed = JSON.parse(candidateJson)
                
                if (parsed.subtasks && Array.isArray(parsed.subtasks)) {
                  console.log("✅ Successfully parsed JSON with", parsed.subtasks.length, "subtasks")
                  return parsed
                } else {
                  console.log("Parsed JSON but no subtasks array, keys:", Object.keys(parsed))
                }
              } catch (parseError) {
                console.log("Failed to parse this JSON candidate, trying next...")
              }
            }
            
            // Try next occurrence of {
            startIndex = jsonStr.indexOf('{', startIndex + 1)
          }
          
          console.warn("Exhausted all JSON candidates, none were valid")
        } catch (error) {
          console.warn("Error during JSON extraction:", error)
        }
      } else {
        console.log("Content doesn't contain both '{' and 'subtasks'")
      }

      // Last resort: Parse the natural language response into subtasks
      console.log("Attempting text parsing as fallback...")
      const subtasks: Subtask[] = []
      const textLines = contentText.split('\n').filter((l) => l.trim())
      
      let currentSubtask: Partial<Subtask> | null = null
      const baseTimestamp = Date.now()
      
      // Helper function to clean markdown and formatting
      const cleanMarkdown = (text: string): string => {
        return text
          .replace(/\*\*/g, '') // Remove bold **
          .replace(/\*/g, '')   // Remove italics *
          .replace(/^[-•]\s*/, '') // Remove leading dash or bullet
          .replace(/^Description:\s*/i, '') // Remove "Description:" prefix
          .replace(/^Title:\s*/i, '') // Remove "Title:" prefix
          .trim()
      }
      
      for (let i = 0; i < textLines.length; i++) {
        const line = textLines[i].trim()
        
        // Skip empty lines and common headers
        if (!line || line.toLowerCase().includes('subtask') && line.length < 15) continue
        
        // Look for numbered items like "1.", "2.", "1)", "Task 1:", etc.
        const numberMatch = line.match(/^(?:Task\s*)?(\d+)[.):]\s*(.+)/i)
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
          
          // Start new subtask
          const titleText = numberMatch[2].trim()
          currentSubtask = {
            title: titleText,
            estimatedHours: 8,
          }
        } else if (currentSubtask && line) {
          // Check for hour estimates (8h, 8 hours, 8hrs, etc.)
          const hourMatch = line.match(/(?:estimated?:?\s*)?(\d+)\s*(?:hours?|hrs?|h)(?:\s|$)/i)
          if (hourMatch) {
            currentSubtask.estimatedHours = parseInt(hourMatch[1])
          } else if (!currentSubtask.description || currentSubtask.description.length < 20) {
            // This line is the description (or start of it)
            currentSubtask.description = cleanMarkdown(line)
          } else if (currentSubtask.description && line.length > 10) {
            // Append to description if it's meaningful
            currentSubtask.description += ' ' + cleanMarkdown(line)
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
        console.log("✅ Generated", subtasks.length, "subtasks from text parsing")
        return { subtasks }
      }

      console.warn("❌ No subtasks found in response, using mock data")
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
    console.log('analyzeMetrics called:', { useMock: this.useMock, request })
    
    if (this.useMock) {
      console.log('Using mock data for metrics')
      return this.mockAnalyzeMetrics(request)
    }

    console.log('Calling platform-engineer-p2p for metrics analysis')
    
    // Call the AI platform engineering backend using streaming API
    const subtasksDescription = request.subtasks
      .map((st, idx) => `${idx + 1}. ${st.title}: ${st.description}`)
      .join('\n')
    
    const prompt = `Analyze the following task and provide metrics:

Title: ${request.title}
Description: ${request.description}

Subtasks:
${subtasksDescription}

IMPORTANT: Respond with ONLY a valid JSON object in this exact format (no markdown, no code blocks, no additional text):

{
  "metrics": [
    {
      "metric": "Impact",
      "value": 75,
      "description": "How this affects the system and users",
      "category": "impact"
    },
    {
      "metric": "Urgency",
      "value": 65,
      "description": "Time sensitivity of this task",
      "category": "urgency"
    },
    {
      "metric": "Complexity",
      "value": 80,
      "description": "Technical complexity and skill requirements",
      "category": "complexity"
    },
    {
      "metric": "Dependencies",
      "value": 55,
      "description": "Dependencies on other systems and tasks",
      "category": "dependencies"
    },
    {
      "metric": "Risk",
      "value": 60,
      "description": "Potential risks and uncertainty",
      "category": "risk"
    }
  ]
}

Provide realistic values (0-100) based on the task and subtasks. Generate exactly 5 metrics with all required fields.`

    try {
      const fullResponse = await this.sendStreamingMessage(prompt)
      
      // Parse the AI response and format it as AnalyzeMetricsResponse
      return this.parseMetricsFromStream(fullResponse, request)
    } catch (error) {
      console.error("Failed to call AI backend for metrics:", error)
      // Fallback to mock data on error
      return this.mockAnalyzeMetrics(request)
    }
  }

  private async parseMetricsFromStream(
    fullResponse: string,
    request: AnalyzeMetricsRequest
  ): Promise<AnalyzeMetricsResponse> {
    try {
      console.log("Parsing metrics AI response, length:", fullResponse.length)
      console.log("Response preview:", fullResponse.substring(0, 300))

      // Parse SSE (Server-Sent Events) format
      const lines = fullResponse.split('\n')
      let contentText = ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonData = JSON.parse(line.substring(6))
            
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
            continue
          }
        }
      }

      console.log("Extracted metrics content length:", contentText.length)
      console.log("Extracted metrics content:", contentText)

      // Try to extract and parse JSON from the content
      let jsonStr = contentText.trim()
      
      // Remove markdown code blocks if present
      if (jsonStr.includes('```')) {
        const codeBlockMatch = jsonStr.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/)
        if (codeBlockMatch) {
          jsonStr = codeBlockMatch[1]
          console.log("Extracted JSON from markdown code block")
        }
      }
      
      // Try to find JSON object in the text
      if (jsonStr.includes("{") && jsonStr.includes("metrics")) {
        try {
          let startIndex = jsonStr.indexOf('{')
          
          // Try each occurrence of { until we find valid JSON
          while (startIndex !== -1 && startIndex < jsonStr.length) {
            let braceCount = 0
            let inString = false
            let escapeNext = false
            let jsonEnd = -1
            
            for (let i = startIndex; i < jsonStr.length; i++) {
              const char = jsonStr[i]
              
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
              const candidateJson = jsonStr.substring(startIndex, jsonEnd + 1)
              console.log("Attempting to parse metrics JSON candidate")
              
              try {
                const parsed = JSON.parse(candidateJson)
                
                if (parsed.metrics && Array.isArray(parsed.metrics)) {
                  console.log("✅ Successfully parsed metrics JSON with", parsed.metrics.length, "metrics")
                  return parsed
                } else {
                  console.log("Parsed JSON but no metrics array, keys:", Object.keys(parsed))
                }
              } catch (parseError) {
                console.log("Failed to parse this JSON candidate, trying next...")
              }
            }
            
            startIndex = jsonStr.indexOf('{', startIndex + 1)
          }
          
          console.warn("Exhausted all metrics JSON candidates")
        } catch (error) {
          console.warn("Error during metrics JSON extraction:", error)
        }
      }

      console.warn("❌ No metrics found in response, using mock data")
      return await this.mockAnalyzeMetrics(request)
    } catch (error) {
      console.error("Failed to parse metrics AI response:", error)
      return await this.mockAnalyzeMetrics(request)
    }
  }

  /**
   * Find user matches for subtask using GitHub MCP
   * API Endpoint: POST /matching/find-candidates
   */
  async findMatches(
    request: FindMatchesRequest
  ): Promise<FindMatchesResponse> {
    console.log('findMatches called:', { useMock: this.useMock, request })
    
    if (this.useMock) {
      console.log('Using mock data for team matching')
      return this.mockFindMatches(request)
    }

    console.log('Calling platform-engineer-p2p for team matching with GitHub MCP')
    
    // Call the AI platform engineering backend using streaming API
    // The AI will use GitHub MCP to analyze PRs and issues
    const githubRepo = request.githubRepo || 'salmanmkc/agentverse'
    
    const prompt = `Find team members for: "${request.subtask.title}"

Subtask: ${request.subtask.description}
Context: ${request.taskTitle}

Known Team Members:
1. Joeclinton1 (Joe Clinton) - AI specialist, GitHub: @Joeclinton1
2. khoinguyenpham04 (Noah/Pham Tran Khoi Nguyen) - Front End specialist, GitHub: @khoinguyenpham04
3. ryanlin10 - Fine tuning models specialist, GitHub: @ryanlin10
4. sul31man - Agentic to agentic specialist, GitHub: @sul31man

Match these team members to the subtask based on their specialties. Use GitHub MCP ONLY if you need to verify activity levels.

Return ONLY JSON (no markdown):
{
  "matches": [
    {
      "user": {"id": "Joeclinton1", "name": "Joe Clinton", "email": "joe@example.com", "avatar": "https://github.com/Joeclinton1.png", "skills": ["AI", "Machine Learning"], "engagement": {"completedTasks": 15, "avgResponseTime": 2, "activeSubtasks": 2, "totalContributions": 50}, "skillDistribution": []},
      "matchPercentage": 90,
      "confidence": 95,
      "rank": 1,
      "reasoning": "AI specialist, perfect match for this task",
      "skillMatches": ["AI"],
      "estimatedCompletionHours": ${request.subtask.estimatedHours || 8},
      "githubActivity": {"openPRs": 1, "closedPRs": 20, "openIssues": 0, "closedIssues": 15}
    }
  ]
}

Return top 3 from the known team, ranks 1-3.`

    try {
      const fullResponse = await this.sendStreamingMessage(prompt)
      
      // Parse the AI response
      return this.parseMatchesFromStream(fullResponse, request)
    } catch (error) {
      console.error("Failed to call AI backend for team matching:", error)
      // Fallback to mock data on error
      return this.mockFindMatches(request)
    }
  }

  private async parseMatchesFromStream(
    fullResponse: string,
    request: FindMatchesRequest
  ): Promise<FindMatchesResponse> {
    try {
      console.log("Parsing team matching AI response, length:", fullResponse.length)
      console.log("Response preview:", fullResponse.substring(0, 300))

      // Parse SSE (Server-Sent Events) format
      const lines = fullResponse.split('\n')
      let contentText = ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonData = JSON.parse(line.substring(6))
            
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
            continue
          }
        }
      }

      console.log("Extracted matches content length:", contentText.length)
      console.log("Extracted matches content:", contentText)

      // Try to extract and parse JSON from the content
      let jsonStr = contentText.trim()
      
      // Remove markdown code blocks if present
      if (jsonStr.includes('```')) {
        const codeBlockMatch = jsonStr.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/)
        if (codeBlockMatch) {
          jsonStr = codeBlockMatch[1]
          console.log("Extracted JSON from markdown code block")
        }
      }
      
      // Try to find JSON object in the text
      if (jsonStr.includes("{") && jsonStr.includes("matches")) {
        try {
          let startIndex = jsonStr.indexOf('{')
          
          // Try each occurrence of { until we find valid JSON
          while (startIndex !== -1 && startIndex < jsonStr.length) {
            let braceCount = 0
            let inString = false
            let escapeNext = false
            let jsonEnd = -1
            
            for (let i = startIndex; i < jsonStr.length; i++) {
              const char = jsonStr[i]
              
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
              const candidateJson = jsonStr.substring(startIndex, jsonEnd + 1)
              console.log("Attempting to parse matches JSON candidate")
              
              try {
                const parsed = JSON.parse(candidateJson)
                
                if (parsed.matches && Array.isArray(parsed.matches)) {
                  console.log("✅ Successfully parsed matches JSON with", parsed.matches.length, "matches")
                  return parsed
                } else {
                  console.log("Parsed JSON but no matches array, keys:", Object.keys(parsed))
                }
              } catch (parseError) {
                console.log("Failed to parse this JSON candidate, trying next...")
              }
            }
            
            startIndex = jsonStr.indexOf('{', startIndex + 1)
          }
          
          console.warn("Exhausted all matches JSON candidates")
        } catch (error) {
          console.warn("Error during matches JSON extraction:", error)
        }
      }

      console.warn("❌ No matches found in response, using mock data")
      return await this.mockFindMatches(request)
    } catch (error) {
      console.error("Failed to parse matches AI response:", error)
      return await this.mockFindMatches(request)
    }
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
      confidence: Math.round(item.score * 0.9), // Slightly lower confidence
      rank: (index + 1) as 1 | 2 | 3,
      reasoning: this.generateReasoning(item.user, request.subtask, item.score),
      skillMatches: item.user.skills.filter((skill) =>
        subtaskLower.includes(skill.toLowerCase())
      ),
      estimatedCompletionHours: Math.round((request.subtask.estimatedHours || 8) * (1 + (index * 0.15))),
      githubActivity: {
        openPRs: Math.floor(Math.random() * 3),
        closedPRs: 10 + Math.floor(Math.random() * 20),
        openIssues: Math.floor(Math.random() * 2),
        closedIssues: 15 + Math.floor(Math.random() * 25),
      },
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

import { features } from "@/config/features"
import { APIConfig } from "@/types/api"

export class APIClient {
  private config: APIConfig

  constructor(config?: Partial<APIConfig>) {
    this.config = {
      baseURL: config?.baseURL || features.API_BASE_URL,
      useMock: config?.useMock ?? !features.USE_REAL_AI,
      timeout: config?.timeout || 30000,
    }
  }

  async post<T>(endpoint: string, data: any): Promise<T> {
    if (this.config.useMock) {
      throw new Error(
        `Mock mode: POST ${endpoint} called. Implement mock handler in service layer.`
      )
    }

    try {
      const response = await fetch(`${this.config.baseURL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
        signal: AbortSignal.timeout(this.config.timeout!),
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error(`API error response:`, errorText)
        throw new Error(
          `API error: ${response.status} ${response.statusText} - ${errorText}`
        )
      }

      return response.json()
    } catch (error) {
      console.error(`API request failed to ${this.config.baseURL}${endpoint}:`, error)
      throw error
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    if (this.config.useMock) {
      throw new Error(
        `Mock mode: GET ${endpoint} called. Implement mock handler in service layer.`
      )
    }

    const response = await fetch(`${this.config.baseURL}${endpoint}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      signal: AbortSignal.timeout(this.config.timeout!),
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`)
    }

    return response.json()
  }
}

export const apiClient = new APIClient()

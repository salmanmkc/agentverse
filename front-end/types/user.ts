export interface User {
  id: string
  name: string
  email: string
  avatar?: string
  skills: string[]
  engagement: {
    completedTasks: number
    avgResponseTime: number // in hours
    activeSubtasks: number
    totalContributions: number
  }
  skillDistribution: {
    skill: string
    value: number // 0-100
  }[]
}

export interface UserMetrics {
  userId: string
  weeklyActivity: {
    week: string
    completed: number
    started: number
  }[]
  strengths: string[]
  badges: string[]
}

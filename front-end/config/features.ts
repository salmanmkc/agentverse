export const features = {
  USE_REAL_AI: process.env.NEXT_PUBLIC_USE_REAL_AI === "true",
  USE_REAL_GITHUB: process.env.NEXT_PUBLIC_USE_REAL_GITHUB === "true",
  ENABLE_CHAT: process.env.NEXT_PUBLIC_ENABLE_CHAT !== "false", // Default to true
  API_BASE_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001/api",
  MOCK_DELAY_MS: parseInt(process.env.NEXT_PUBLIC_MOCK_DELAY_MS || "1500"), // Simulate API delay
}

export const isDevelopment = process.env.NODE_ENV === "development"

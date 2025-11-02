# Backend API Integration Guide

This document describes how to integrate the frontend with your real AI backend.

## Quick Start

1. Set environment variables:
```bash
# .env.local
NEXT_PUBLIC_USE_REAL_AI=true
NEXT_PUBLIC_API_URL=https://your-backend.com/api
NEXT_PUBLIC_MOCK_DELAY_MS=0  # Optional: remove simulated delays
```

2. Restart the development server

3. All AI features will now call your real backend

## API Endpoints

Your backend must implement the following endpoints:

### 1. Generate Subtasks
**Endpoint:** `POST /tasks/generate-subtasks`

**Request Body:**
```typescript
{
  title: string
  description: string
  context?: string  // Optional: comma-separated tags
}
```

**Response:**
```typescript
{
  subtasks: Array<{
    id: string
    title: string
    description: string
    status: "open" | "in_progress" | "completed"
    assignedTo: User[]
    createdAt: string  // ISO 8601
    updatedAt: string  // ISO 8601
    estimatedHours?: number
  }>
}
```

**What it should do:**
- Analyze the task title and description
- Generate 3-5 actionable subtasks
- Provide clear titles and descriptions
- Estimate hours if possible

---

### 2. Analyze Metrics
**Endpoint:** `POST /tasks/analyze-metrics`

**Request Body:**
```typescript
{
  title: string
  description: string
  subtasks: Subtask[]
}
```

**Response:**
```typescript
{
  metrics: Array<{
    metric: string  // e.g., "Impact", "Urgency", "Complexity"
    value: number   // 0-100
    description: string
    category: "impact" | "urgency" | "complexity" | "dependencies" | "risk"
  }>
}
```

**What it should do:**
- Analyze the task's importance and characteristics
- Return exactly 5 metrics with values 0-100
- Provide clear descriptions of why each metric has that value
- Cover: Impact, Urgency, Complexity, Dependencies, Risk

---

### 3. Find User Matches
**Endpoint:** `POST /matching/find-candidates`

**Request Body:**
```typescript
{
  subtask: {
    id: string
    title: string
    description: string
    estimatedHours?: number
  }
  availableUserIds?: string[]  // Optional: restrict to specific users
}
```

**Response:**
```typescript
{
  matches: Array<{
    user: User  // Full user object
    matchPercentage: number  // 0-100
    rank: 1 | 2 | 3  // Top 3 matches
    reasoning: string  // Explain why this match is good
    skillMatches: string[]  // Which skills matched
  }>
}
```

**What it should do:**
- Analyze subtask requirements
- Match against available users' skills
- Consider user availability (activeSubtasks count)
- Return top 3 matches ranked by fit
- Provide clear reasoning

---

### 4. Create GitHub Issues
**Endpoint:** `POST /github/create-issues`

**Request Body:**
```typescript
{
  taskTitle: string
  subtasks: Array<{
    subtaskId: string
    assignedUserId: string
  }>
  repository?: string  // e.g., "owner/repo"
  projectBoard?: string  // Optional project board
}
```

**Response:**
```typescript
{
  issueUrls: string[]  // One URL per subtask
  projectUrl?: string  // Project board URL if created
}
```

**What it should do:**
- Create GitHub issue for each subtask
- Assign to the specified user (map userId to GitHub username)
- Add to project board if specified
- Return URLs to created issues

---

## Error Handling

All endpoints should return appropriate HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid input)
- `401` - Unauthorized
- `500` - Server error

Error response format:
```typescript
{
  error: string
  message: string
  details?: any
}
```

---

## Frontend Service Architecture

The frontend uses a service layer that abstracts API calls:

```
User Interaction
       ↓
  UI Components
       ↓
  Service Layer (services/ai-service.ts)
       ↓
  API Client (services/api-client.ts)
       ↓
  Your Backend API
```

**Key Files:**
- `services/ai-service.ts` - Main AI service with mock implementations
- `services/api-client.ts` - HTTP client wrapper
- `config/features.ts` - Feature flags and configuration

---

## Testing Integration

1. **Start with Mock Data:**
   - Set `NEXT_PUBLIC_USE_REAL_AI=false`
   - Test UI flow with mock responses

2. **Enable Real API:**
   - Set `NEXT_PUBLIC_USE_REAL_AI=true`
   - Test each endpoint individually

3. **Check Network Tab:**
   - Open browser DevTools
   - Monitor API calls in Network tab
   - Verify request/response formats

4. **Error Scenarios:**
   - Test with invalid inputs
   - Simulate API failures
   - Check error messages display correctly

---

## Additional Configuration

### Timeout
Default timeout is 30 seconds. Adjust in `services/api-client.ts`:
```typescript
timeout: 30000  // milliseconds
```

### Authentication
If your API requires authentication, update `api-client.ts`:
```typescript
headers: {
  "Content-Type": "application/json",
  "Authorization": `Bearer ${YOUR_AUTH_TOKEN}`,
}
```

### CORS
Ensure your backend allows requests from your frontend domain.

---

## Mock vs Real API Comparison

| Feature | Mock (Current) | Real API (To Implement) |
|---------|---------------|------------------------|
| Subtask Generation | Template-based | AI-powered analysis |
| Metrics Analysis | Hash-based calculation | Real complexity analysis |
| User Matching | Simple keyword matching | ML-based recommendations |
| GitHub Integration | Fake URLs | Real issue creation |
| Response Time | ~1.5 seconds | Variable |

---

## Troubleshooting

**API calls not working?**
1. Check environment variables are set correctly
2. Verify API URL is accessible
3. Check browser console for errors
4. Test API endpoints directly with curl/Postman

**Seeing "Mock mode" errors?**
- `USE_REAL_AI` is still false
- Restart dev server after changing env vars

**Slow responses?**
- Check `MOCK_DELAY_MS` setting
- Monitor actual API response times
- Consider adding loading states

---

## Next Steps

1. Implement the 4 required endpoints
2. Test each endpoint with curl/Postman
3. Enable real API in frontend
4. Test full flow end-to-end
5. Monitor and optimize performance

---

## Support

For frontend issues or questions:
- Check `ARCHITECTURE.md` for overall design
- Review `IMPLEMENTATION_PLAN.md` for details
- Check service layer code for implementation examples

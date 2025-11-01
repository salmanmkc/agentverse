# Implementation Plan - Task Management System

## Phase 1: Foundation & Data Models

### 1.1 Create TypeScript Types
- `types/task.ts` - Task, Subtask interfaces
- `types/user.ts` - User, Skill, Engagement interfaces
- `types/api.ts` - API request/response types

### 1.2 Create Mock AI Service Layer
```typescript
// services/ai-service.ts
class AIService {
  // Mock with delays to simulate API calls
  async generateSubtasks(taskDescription: string): Promise<Subtask[]>
  async analyzeMetrics(task: Task): Promise<Metric[]>
  async findMatches(subtask: Subtask, users: User[]): Promise<Match[]>

  // Easy backend integration point:
  // Just change this flag and point to real API
  private useMockData = true
  private apiEndpoint = process.env.NEXT_PUBLIC_AI_API_URL
}
```

### 1.3 Create Mock Data
- Sample tasks (open and closed)
- Sample users with skills and metrics
- Sample subtasks and allocations

## Phase 2: Dashboard Refactor

### 2.1 Update Dashboard Layout
- Remove or repurpose existing SectionCards for task metrics
- Create new unified view with:
  - Top: Quick stats (open tasks, team members, completion rate)
  - Main: Task list with inline user assignments
  - Side panels: Filters and quick user directory

### 2.2 Task Display Components
- `TaskCard` - Shows task with progress, subtasks, assigned users
- `TaskListView` - Open tasks prominently displayed
- `ClosedTasksSection` - Collapsible with completion stats
- `SubtaskList` - Nested subtask view with assignments

### 2.3 User Integration
- User avatars on tasks showing assignments
- Quick user panel showing who's working on what
- User skill badges

## Phase 3: Task Creation Modal

### 3.1 Modal Infrastructure
- Dialog component with full-screen overlay
- Smooth expand animation from button
- Step indicator showing progress (1/5, 2/5, etc.)
- Back/Next navigation
- Cancel with confirmation

### 3.2 Step 1: Define Task Component
```typescript
// components/tasks/steps/step1-define-task.tsx
- Title input
- Description textarea
- Priority selector (low/medium/high)
- Tags input
- Context/goals textarea
```

### 3.3 Step 2: Subtask Generation
```typescript
// components/tasks/steps/step2-subtasks.tsx
- Trigger AI generation button
- Loading state with animation
- Display generated subtasks as cards
- Each card:
  - Title
  - Description
  - "Break down further" button (recursive)
- Approve/Regenerate buttons
```

### 3.4 Step 3: Metric Analysis
```typescript
// components/tasks/steps/step3-metrics.tsx
- Multi-step pipeline visualization
- Radar chart component for metrics
- Metric cards explaining importance
- Mock metrics: impact, urgency, complexity, dependencies
```

### 3.5 Step 4: AI Matching
```typescript
// components/tasks/steps/step4-matching.tsx
- Animated matching process:
  - "Analyzing team members..." phase
  - "Comparing skills..." phase
  - "Finding best matches..." phase
- For each subtask:
  - Show top 3 user matches
  - #1: Highlighted with check icon
  - #2, #3: Grayed with match percentage
  - Ability to manually select different person
```

### 3.6 Step 5: Allocation
```typescript
// components/tasks/steps/step5-allocation.tsx
- Summary of all allocations
- GitHub integration options:
  - Create repository issues
  - Add to project board
- Notification settings
- Final "Create Task" button
```

## Phase 4: Visualizations

### 4.1 Radar Chart Component
```typescript
// components/visualizations/radar-chart.tsx
- Using recharts library (already in dependencies)
- Skills radar for users
- Metrics radar for tasks
- Smooth animations
```

### 4.2 Matching Animation
```typescript
// components/visualizations/matching-animation.tsx
- Simulated AI thinking with:
  - Connecting lines between users and subtasks
  - Percentage counters animating up
  - Pulsing effects
  - Graph visualizations
```

### 4.3 Progress Visualizations
- Progress bars for tasks
- Completion rings for user metrics
- Timeline views

## Phase 5: Chat Sidebar Integration

### 5.1 Conditional Chat Sidebar
- Only render during task creation
- Show during Steps 1-2 (task description and breakdown)
- Hide during Steps 3-5
- Smooth slide-in animation
- Connected to mock AI chat service

### 5.2 Chat Interface
```typescript
// Update existing ChatbotSidebar to:
- Accept context (current task being created)
- Allow asking questions about task breakdown
- Show AI responses for subtask suggestions
- Mock conversation flow
```

## Phase 6: Backend Integration Prep

### 6.1 API Service Abstraction
```typescript
// services/api-client.ts
interface APIClient {
  post<T>(endpoint: string, data: any): Promise<T>
  get<T>(endpoint: string): Promise<T>
}

// Development: returns mock data
// Production: calls real API
const client = createAPIClient({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  useMock: process.env.NODE_ENV === 'development'
})
```

### 6.2 Integration Points Documentation
```typescript
// API_INTEGRATION.md
Document all endpoints:
- POST /api/tasks - Create task
- POST /api/tasks/:id/subtasks/generate - Generate subtasks
- POST /api/tasks/:id/metrics - Analyze metrics
- POST /api/matching/find - Find user matches
- POST /api/github/create-issues - Create GitHub issues
```

### 6.3 Feature Flags
```typescript
// config/features.ts
export const features = {
  USE_REAL_AI: process.env.NEXT_PUBLIC_USE_REAL_AI === 'true',
  USE_REAL_GITHUB: process.env.NEXT_PUBLIC_USE_REAL_GITHUB === 'true',
  ENABLE_CHAT: process.env.NEXT_PUBLIC_ENABLE_CHAT === 'true',
}
```

## Implementation Order

1. **Day 1: Foundation**
   - Create all types
   - Create mock AI service
   - Create mock data
   - Set up service layer structure

2. **Day 2: Dashboard**
   - Refactor dashboard page
   - Create TaskCard component
   - Create UserCard component
   - Integrate mock data display

3. **Day 3: Modal Steps 1-2**
   - Create modal infrastructure
   - Implement Step 1 (Define Task)
   - Implement Step 2 (Subtask Generation with mock AI)

4. **Day 4: Modal Steps 3-5**
   - Implement Step 3 (Metrics with radar chart)
   - Implement Step 4 (Matching with animation)
   - Implement Step 5 (Allocation)

5. **Day 5: Polish & Integration**
   - Chat sidebar conditional rendering
   - Animations and transitions
   - Connect all pieces
   - Test full flow
   - Document backend integration points

## Key Principles

1. **Separation of Concerns**: UI components never call AI directly, always through service layer
2. **Mock First**: All AI features work with mocks, easy to swap
3. **Type Safety**: Strong TypeScript types for all data
4. **Smooth UX**: Animations and loading states everywhere
5. **Easy Integration**: Clear documentation and integration points for backend team

## Dependencies Already Available
- @radix-ui components (dialog, progress, etc.)
- recharts (for radar charts)
- motion (for animations)
- @dnd-kit (for drag and drop)
- All UI components already built

## New Files to Create
- ~15 new TypeScript files
- ~10 new component files
- 3-4 service files
- Type definition files
- Mock data files

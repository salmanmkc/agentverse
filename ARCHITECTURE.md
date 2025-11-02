# AgentVerse Task Management Architecture

## Overview
A task management system with AI-powered task breakdown, matching, and allocation.

## Key Features

### 1. Dashboard (Merged Tasks + Users)
- Single view showing both tasks and user information
- Open tasks with progress bars and assigned members
- Closed tasks in collapsible section with stats
- Subtasks nested under each task
- Quick allocations panel
- Filtering by status, priority, assignee
- User metrics cards showing engagement and skills

### 2. Task Creation Flow (5-Step Modal)
Opens via "Create Task" button with smooth animation expansion.

**Step 1: Define Task**
- Title, description, metadata (priority, tags)
- Context and goals
- Simple form interface

**Step 2: AI-Generated Subtasks**
- AI automatically generates subtasks
- Each subtask as card with title + description
- Click any subtask to recursively break it down further
- Approve button to proceed

**Step 3: Metric Analysis**
- Multi-step pipeline identifies key metrics
- Radar charts showing why task matters
- Visual metric displays

**Step 4: Matching Process**
- AI finds best people for each subtask
- Animated "AI thinking" visualization
- Shows comparisons, graphs, connecting lines
- Top 3 matches per subtask:
  - #1: Highlighted
  - #2 & #3: Grayed with percentages

**Step 5: Allocation & Integration**
- Assign chosen people to subtasks
- Push to GitHub (issues/projects)
- Notify assignees

### 3. Chat Sidebar Integration
- Only visible during task creation
- Used for AI interactions during task breakdown
- Hidden otherwise
- Slides in/out with animation

### 4. User Metrics & Insights
- Engagement graphs (completed subtasks, response time)
- Radar charts for skill distribution
- Match accuracy insights
- Badges highlighting strengths

## Technical Architecture

### Data Layer
- TypeScript interfaces for Task, Subtask, User
- Mock data for development
- Clear separation between data and presentation

### AI Service Layer
**Mock Implementation (Current)**
- Stubbed AI services with simulated delays
- Fake data generation
- Animated "thinking" effects

**Integration Points (Future)**
- `/api/tasks/generate-subtasks` - Generate subtasks from task description
- `/api/tasks/analyze-metrics` - Analyze task metrics
- `/api/matching/find-candidates` - Match users to subtasks
- `/api/github/create-issues` - Create GitHub issues
- Clear service interfaces for easy backend swap

### Component Structure
```
app/
  dashboard/
    page.tsx - Main dashboard (refactored)
components/
  tasks/
    task-card.tsx - Task display card
    task-list.tsx - List of tasks
    subtask-card.tsx - Subtask display
    task-creation-modal.tsx - Main modal
    steps/
      step1-define-task.tsx
      step2-subtasks.tsx
      step3-metrics.tsx
      step4-matching.tsx
      step5-allocation.tsx
  users/
    user-card.tsx - User info card
    user-metrics.tsx - User metrics display
  visualizations/
    radar-chart.tsx - Skill/metric radar
    matching-animation.tsx - AI matching viz
services/
  ai-service.ts - Mock AI (with integration points)
  task-service.ts - Task management
  user-service.ts - User management
types/
  task.ts - Task-related types
  user.ts - User-related types
```

## Animation & UX
- Smooth modal expansion when creating task
- Animated step transitions
- AI "thinking" animations with visual flair
- Progress indicators
- Smooth transitions between states

## Backend Integration Strategy
1. All AI calls isolated in service layer
2. Environment variable for API endpoint
3. Feature flags for mock vs real AI
4. Clear TypeScript interfaces for API contracts
5. Easy swap: change service implementation, keep components unchanged

## Current State
- Using existing dashboard structure
- Has SectionCards, DataTable, ChartAreaInteractive
- ChatbotSidebar already exists on right
- Need to refactor to merge task/user view
- Add task creation modal overlay

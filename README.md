# AgentVerse - AI-Powered Task Management

An intelligent task management system with AI-powered task breakdown, team matching, and allocation.

## Features

- 🎯 **Smart Task Creation** - AI generates actionable subtasks from descriptions
- 📊 **Metric Analysis** - Understand task impact, urgency, and complexity
- 🤝 **Intelligent Matching** - AI matches team members to subtasks based on skills
- 👯 **Digital Twins** - Personalised agents finetuned to each team member's preferences, workplace style, and reactions
- 📈 **Visual Dashboard** - Track tasks, progress, and team performance
- 🔄 **GitHub Integration** - Automatically create issues and manage projects
- 🎨 **Modern UI** - Beautiful, responsive interface with smooth animations

## Quick Start

```bash
# Install dependencies
cd front-end
npm install

# Start development server
npm run dev

# Visit http://localhost:3000/dashboard
```

## Project Structure

```
agentverse/
├── front-end/               # Next.js application
│   ├── app/                 # Next.js pages
│   ├── components/          # React components
│   ├── services/            # API & business logic
│   ├── types/               # TypeScript definitions
│   ├── lib/                 # Utilities & mock data
│   └── config/              # Configuration
├── ARCHITECTURE.md          # System design overview
├── IMPLEMENTATION_PLAN.md   # Detailed implementation guide
├── API_INTEGRATION.md       # Backend integration instructions
└── IMPLEMENTATION_SUMMARY.md # What was built
```

## Documentation

- **[Architecture](ARCHITECTURE.md)** - System design and component structure
- **[Implementation Plan](IMPLEMENTATION_PLAN.md)** - Phase-by-phase development plan
- **[API Integration](API_INTEGRATION.md)** - How to connect your AI backend
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Complete feature overview

## Current Status

✅ **Frontend Complete** - Fully functional with mock AI
🔄 **Backend Integration** - Ready for real AI endpoints
📋 **Mock Data** - 6 team members, 5 sample tasks

## Backend Integration

The frontend is ready to connect to your AI backend. You need to implement 4 endpoints:

1. `POST /tasks/generate-subtasks` - Generate subtasks from task description
2. `POST /tasks/analyze-metrics` - Analyze task metrics
3. `POST /matching/find-candidates` - Match users to subtasks
4. `POST /github/create-issues` - Create GitHub issues

See [API_INTEGRATION.md](API_INTEGRATION.md) for detailed specs.

### Enable Real Backend

```bash
# .env.local
NEXT_PUBLIC_USE_REAL_AI=true
NEXT_PUBLIC_API_URL=https://your-backend.com/api
```

## Tech Stack

- **Framework:** Next.js 16 with React 19
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **UI Components:** Radix UI
- **Charts:** Recharts
- **Animations:** Motion (framer-motion)

## Key Features

### Dashboard
- Task statistics and metrics
- Open and closed task views
- Team member directory
- Expandable subtask lists

### Task Creation (5 Steps)
1. **Define Task** - Title, description, priority, tags
2. **Generate Subtasks** - AI-powered breakdown (with recursive decomposition)
3. **Analyze Metrics** - Visualize impact, urgency, complexity with radar charts
4. **Match Team** - AI finds top 3 candidates for each subtask
5. **Allocate & Deploy** - Review allocations, create GitHub issues

### Visualizations
- Radar charts for metrics
- Progress bars for tasks
- User skill distributions
- Animated matching process

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Environment Variables

```bash
# Optional - defaults provided
NEXT_PUBLIC_USE_REAL_AI=false          # Use real AI backend
NEXT_PUBLIC_API_URL=http://localhost:3001/api  # Backend URL
NEXT_PUBLIC_USE_REAL_GITHUB=false      # Use real GitHub API
NEXT_PUBLIC_ENABLE_CHAT=true           # Enable chat sidebar
NEXT_PUBLIC_MOCK_DELAY_MS=1500         # Simulated API delay
```

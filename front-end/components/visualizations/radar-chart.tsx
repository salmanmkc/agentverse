"use client"

import { TaskMetric } from "@/types/task"
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"

interface MetricRadarChartProps {
  metrics: TaskMetric[]
}

export function MetricRadarChart({ metrics }: MetricRadarChartProps) {
  const chartData = metrics.map((m) => ({
    metric: m.metric,
    value: m.value,
  }))

  const chartConfig = {
    value: {
      label: "Score",
      color: "hsl(var(--primary))",
    },
  } satisfies ChartConfig

  return (
    <ChartContainer config={chartConfig} className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={chartData}>
          <PolarGrid />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
          />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} />
          <Radar
            name="Score"
            dataKey="value"
            stroke="hsl(var(--primary))"
            fill="hsl(var(--primary))"
            fillOpacity={0.6}
          />
          <ChartTooltip content={<ChartTooltipContent />} />
        </RadarChart>
      </ResponsiveContainer>
    </ChartContainer>
  )
}

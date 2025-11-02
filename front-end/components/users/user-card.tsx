"use client"

import { User } from "@/types/user"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  IconBriefcase,
  IconClock,
  IconTarget,
} from "@tabler/icons-react"

interface UserCardProps {
  user: User
  compact?: boolean
}

export function UserCard({ user, compact = false }: UserCardProps) {
  if (compact) {
    return (
      <div className="flex items-center gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
        <Avatar className="size-10">
          <AvatarImage src={user.avatar} alt={user.name} />
          <AvatarFallback>
            {user.name
              .split(" ")
              .map((n) => n[0])
              .join("")}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm truncate">{user.name}</h4>
          <p className="text-xs text-muted-foreground truncate">{user.email}</p>
        </div>
        <Badge variant="secondary" className="text-xs">
          {user.engagement.activeSubtasks} active
        </Badge>
      </div>
    )
  }

  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start gap-4">
          <Avatar className="size-12">
            <AvatarImage src={user.avatar} alt={user.name} />
            <AvatarFallback>
              {user.name
                .split(" ")
                .map((n) => n[0])
                .join("")}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base">{user.name}</CardTitle>
            <p className="text-sm text-muted-foreground truncate">
              {user.email}
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Skills */}
        <div>
          <p className="text-xs text-muted-foreground mb-2">Skills</p>
          <div className="flex flex-wrap gap-1">
            {user.skills.slice(0, 4).map((skill) => (
              <Badge key={skill} variant="secondary" className="text-xs">
                {skill}
              </Badge>
            ))}
            {user.skills.length > 4 && (
              <Badge variant="outline" className="text-xs">
                +{user.skills.length - 4}
              </Badge>
            )}
          </div>
        </div>

        {/* Engagement Metrics */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <IconTarget className="size-4" />
              <span>Completed</span>
            </div>
            <span className="font-medium">
              {user.engagement.completedTasks}
            </span>
          </div>

          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <IconBriefcase className="size-4" />
              <span>Active</span>
            </div>
            <span className="font-medium">
              {user.engagement.activeSubtasks}
            </span>
          </div>

          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <IconClock className="size-4" />
              <span>Avg Response</span>
            </div>
            <span className="font-medium">
              {user.engagement.avgResponseTime}h
            </span>
          </div>
        </div>

        {/* Status Badge */}
        <div className="pt-2 border-t">
          {user.engagement.activeSubtasks === 0 ? (
            <Badge variant="outline" className="bg-green-500/10 text-green-700 dark:text-green-400">
              Available
            </Badge>
          ) : user.engagement.activeSubtasks < 3 ? (
            <Badge variant="outline" className="bg-blue-500/10 text-blue-700 dark:text-blue-400">
              Moderate Load
            </Badge>
          ) : (
            <Badge variant="outline" className="bg-yellow-500/10 text-yellow-700 dark:text-yellow-400">
              High Load
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

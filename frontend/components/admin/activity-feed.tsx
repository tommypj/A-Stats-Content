"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AdminAuditLog } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import {
  UserPlus,
  UserMinus,
  FileText,
  Image,
  Shield,
  Settings,
  Trash2,
  Edit,
  LucideIcon,
} from "lucide-react";
import { clsx } from "clsx";

interface ActivityFeedProps {
  activities: AdminAuditLog[];
  loading?: boolean;
}

const ACTION_ICONS: Record<string, LucideIcon> = {
  "user.created": UserPlus,
  "user.updated": Edit,
  "user.deleted": UserMinus,
  "user.suspended": Shield,
  "article.created": FileText,
  "article.deleted": Trash2,
  "image.generated": Image,
  "settings.updated": Settings,
};

const ACTION_COLORS: Record<string, string> = {
  created: "bg-green-100 text-green-600",
  updated: "bg-blue-100 text-blue-600",
  deleted: "bg-red-100 text-red-600",
  suspended: "bg-yellow-100 text-yellow-600",
  generated: "bg-purple-100 text-purple-600",
};

function getActionColor(action: string): string {
  if (action.includes("created")) return ACTION_COLORS.created;
  if (action.includes("updated")) return ACTION_COLORS.updated;
  if (action.includes("deleted")) return ACTION_COLORS.deleted;
  if (action.includes("suspended")) return ACTION_COLORS.suspended;
  if (action.includes("generated")) return ACTION_COLORS.generated;
  return "bg-surface-tertiary text-text-muted";
}

export function ActivityFeed({ activities, loading }: ActivityFeedProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="h-10 w-10 rounded-full bg-surface-tertiary animate-pulse" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-surface-tertiary rounded w-3/4 animate-pulse" />
                  <div className="h-3 bg-surface-tertiary rounded w-1/2 animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (activities.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-muted text-center py-8">
            No recent activity to display
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {activities.map((activity) => {
            const Icon = ACTION_ICONS[activity.action] || FileText;
            const colorClass = getActionColor(activity.action);

            return (
              <div key={activity.id} className="flex items-start gap-3">
                <div
                  className={clsx(
                    "h-10 w-10 rounded-full flex items-center justify-center flex-shrink-0",
                    colorClass
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary">
                    {activity.user_email || "System"}
                    <span className="text-text-secondary font-normal ml-1">
                      {activity.action.replace(".", " ").replace("_", " ")}
                    </span>
                  </p>
                  {activity.resource_type && (
                    <p className="text-xs text-text-muted mt-0.5">
                      {activity.resource_type}
                      {activity.resource_id && ` #${activity.resource_id.slice(0, 8)}`}
                    </p>
                  )}
                  <p className="text-xs text-text-muted mt-1">
                    {formatDistanceToNow(new Date(activity.created_at), {
                      addSuffix: true,
                    })}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

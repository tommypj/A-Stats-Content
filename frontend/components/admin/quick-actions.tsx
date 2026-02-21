"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Users,
  FileText,
  BarChart3,
  Settings,
  ScrollText,
  LucideIcon,
} from "lucide-react";

interface QuickAction {
  label: string;
  href: string;
  icon: LucideIcon;
  description: string;
}

const quickActions: QuickAction[] = [
  {
    label: "Manage Users",
    href: "/admin/users",
    icon: Users,
    description: "View and manage user accounts",
  },
  {
    label: "View Content",
    href: "/admin/content/articles",
    icon: FileText,
    description: "Browse all articles and content",
  },
  {
    label: "View Analytics",
    href: "/admin/analytics",
    icon: BarChart3,
    description: "Check system analytics",
  },
  {
    label: "Audit Logs",
    href: "/admin/audit-logs",
    icon: ScrollText,
    description: "Review system activity logs",
  },
  {
    label: "Settings",
    href: "/admin/settings",
    icon: Settings,
    description: "Configure system settings",
  },
];

export function QuickActions() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {quickActions.map((action) => (
            <Link key={action.href} href={action.href}>
              <Button
                variant="outline"
                className="w-full h-auto flex flex-col items-start p-4 hover:border-purple-300 hover:bg-purple-50 transition-colors"
              >
                <div className="flex items-center gap-2 w-full mb-2">
                  <action.icon className="h-5 w-5 text-purple-600" />
                  <span className="font-medium text-text-primary">{action.label}</span>
                </div>
                <p className="text-xs text-text-muted text-left">
                  {action.description}
                </p>
              </Button>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

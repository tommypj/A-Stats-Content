"use client";

import Link from "next/link";
import {
  FileText,
  Sparkles,
  Image as ImageIcon,
  TrendingUp,
  ArrowRight,
  Plus,
  Clock,
  CheckCircle2,
} from "lucide-react";

const stats = [
  { name: "Total Articles", value: "0", icon: FileText, change: "+0%" },
  { name: "Outlines Created", value: "0", icon: Sparkles, change: "+0%" },
  { name: "Images Generated", value: "0", icon: ImageIcon, change: "+0%" },
  { name: "SEO Score Avg", value: "N/A", icon: TrendingUp, change: "0%" },
];

const quickActions = [
  {
    name: "Create Outline",
    description: "Start with AI-generated structure",
    icon: FileText,
    href: "/outlines/new",
    color: "bg-healing-sage",
  },
  {
    name: "Write Article",
    description: "Generate SEO-optimized content",
    icon: Sparkles,
    href: "/articles/new",
    color: "bg-healing-lavender",
  },
  {
    name: "Generate Image",
    description: "Create custom AI images",
    icon: ImageIcon,
    href: "/images/new",
    color: "bg-healing-sky",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8 animate-in">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Welcome back!
        </h1>
        <p className="mt-1 text-text-secondary">
          Here's an overview of your content creation activity.
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.name} className="card p-5">
            <div className="flex items-center justify-between">
              <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center">
                <stat.icon className="h-5 w-5 text-primary-500" />
              </div>
              <span className="text-xs font-medium text-healing-sage">
                {stat.change}
              </span>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-display font-bold text-text-primary">
                {stat.value}
              </p>
              <p className="text-sm text-text-muted">{stat.name}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-lg font-display font-semibold text-text-primary mb-4">
          Quick Actions
        </h2>
        <div className="grid sm:grid-cols-3 gap-4">
          {quickActions.map((action) => (
            <Link
              key={action.name}
              href={action.href}
              className="card p-5 hover:shadow-md transition-all group"
            >
              <div
                className={`h-12 w-12 rounded-xl ${action.color} flex items-center justify-center mb-4`}
              >
                <action.icon className="h-6 w-6 text-white" />
              </div>
              <h3 className="font-display font-semibold text-text-primary group-hover:text-primary-600 transition-colors">
                {action.name}
              </h3>
              <p className="text-sm text-text-secondary mt-1">
                {action.description}
              </p>
              <div className="flex items-center gap-1 mt-3 text-sm text-primary-500 font-medium">
                <span>Get started</span>
                <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent activity */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Recent outlines */}
        <div className="card">
          <div className="flex items-center justify-between p-5 border-b border-surface-tertiary">
            <h2 className="font-display font-semibold text-text-primary">
              Recent Outlines
            </h2>
            <Link
              href="/outlines"
              className="text-sm text-primary-500 hover:text-primary-600 font-medium"
            >
              View all
            </Link>
          </div>
          <div className="p-5">
            <div className="text-center py-8">
              <div className="h-12 w-12 rounded-xl bg-surface-secondary flex items-center justify-center mx-auto mb-3">
                <FileText className="h-6 w-6 text-text-muted" />
              </div>
              <p className="text-text-secondary text-sm">No outlines yet</p>
              <Link
                href="/outlines/new"
                className="inline-flex items-center gap-1 mt-3 text-sm text-primary-500 hover:text-primary-600 font-medium"
              >
                <Plus className="h-4 w-4" />
                Create your first outline
              </Link>
            </div>
          </div>
        </div>

        {/* Recent articles */}
        <div className="card">
          <div className="flex items-center justify-between p-5 border-b border-surface-tertiary">
            <h2 className="font-display font-semibold text-text-primary">
              Recent Articles
            </h2>
            <Link
              href="/articles"
              className="text-sm text-primary-500 hover:text-primary-600 font-medium"
            >
              View all
            </Link>
          </div>
          <div className="p-5">
            <div className="text-center py-8">
              <div className="h-12 w-12 rounded-xl bg-surface-secondary flex items-center justify-center mx-auto mb-3">
                <Sparkles className="h-6 w-6 text-text-muted" />
              </div>
              <p className="text-text-secondary text-sm">No articles yet</p>
              <Link
                href="/articles/new"
                className="inline-flex items-center gap-1 mt-3 text-sm text-primary-500 hover:text-primary-600 font-medium"
              >
                <Plus className="h-4 w-4" />
                Create your first article
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Usage & Plan */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display font-semibold text-text-primary">
            Usage This Month
          </h2>
          <Link
            href="/settings/billing"
            className="text-sm text-primary-500 hover:text-primary-600 font-medium"
          >
            Upgrade Plan
          </Link>
        </div>
        <div className="grid sm:grid-cols-3 gap-4">
          <div>
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-text-secondary">Articles</span>
              <span className="text-text-primary font-medium">0 / 10</span>
            </div>
            <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden">
              <div className="h-full w-0 bg-primary-500 rounded-full" />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-text-secondary">Outlines</span>
              <span className="text-text-primary font-medium">0 / 20</span>
            </div>
            <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden">
              <div className="h-full w-0 bg-healing-sage rounded-full" />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-text-secondary">Images</span>
              <span className="text-text-primary font-medium">0 / 5</span>
            </div>
            <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden">
              <div className="h-full w-0 bg-healing-lavender rounded-full" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

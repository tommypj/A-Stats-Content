"use client";

import { Card } from "@/components/ui/card";
import {
  Settings,
  Server,
  Shield,
  Globe,
  Database,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

export default function AdminSettingsPage() {
  return (
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Admin Settings</h1>
        <p className="mt-1 text-text-secondary">System configuration and platform settings.</p>
      </div>

      {/* System Status */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Server className="h-5 w-5 text-primary-500" />
          <h2 className="text-lg font-display font-semibold text-text-primary">System Status</h2>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <StatusItem label="API Server" status="operational" />
          <StatusItem label="Database" status="operational" />
          <StatusItem label="Redis Cache" status="operational" />
          <StatusItem label="AI Services" status="operational" />
          <StatusItem label="Email (Resend)" status="operational" />
          <StatusItem label="Payments (LemonSqueezy)" status="operational" />
        </div>
      </Card>

      {/* Service Configuration */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="h-5 w-5 text-primary-500" />
          <h2 className="text-lg font-display font-semibold text-text-primary">
            Service Configuration
          </h2>
        </div>
        <div className="space-y-3">
          <ConfigItem
            label="Anthropic API"
            description="AI content generation"
            configured={true}
          />
          <ConfigItem
            label="Replicate API"
            description="AI image generation"
            configured={true}
          />
          <ConfigItem
            label="OpenAI API"
            description="Text embeddings"
            configured={true}
          />
          <ConfigItem
            label="Resend"
            description="Transactional emails"
            configured={true}
          />
          <ConfigItem
            label="LemonSqueezy"
            description="Payment processing"
            configured={true}
          />
          <ConfigItem
            label="Google OAuth"
            description="Search Console integration"
            configured={true}
          />
        </div>
        <p className="text-xs text-text-muted mt-4">
          Service configuration is managed via environment variables. Update settings in your
          Railway dashboard.
        </p>
      </Card>

      {/* Platform Info */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Globe className="h-5 w-5 text-primary-500" />
          <h2 className="text-lg font-display font-semibold text-text-primary">Platform Info</h2>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between py-2 border-b border-surface-tertiary">
            <span className="text-text-secondary">App Version</span>
            <span className="text-text-primary font-medium">2.0.0</span>
          </div>
          <div className="flex justify-between py-2 border-b border-surface-tertiary">
            <span className="text-text-secondary">Environment</span>
            <span className="text-text-primary font-medium">Production</span>
          </div>
          <div className="flex justify-between py-2 border-b border-surface-tertiary">
            <span className="text-text-secondary">Backend</span>
            <span className="text-text-primary font-medium">FastAPI + Python 3.11</span>
          </div>
          <div className="flex justify-between py-2">
            <span className="text-text-secondary">Frontend</span>
            <span className="text-text-primary font-medium">Next.js 14 + React 18</span>
          </div>
        </div>
      </Card>
    </div>
  );
}

function StatusItem({ label, status }: { label: string; status: "operational" | "degraded" | "down" }) {
  return (
    <div className="flex items-center justify-between p-3 bg-surface-secondary rounded-xl">
      <span className="text-sm text-text-primary">{label}</span>
      {status === "operational" ? (
        <span className="flex items-center gap-1 text-xs text-green-600">
          <CheckCircle className="h-3.5 w-3.5" /> Operational
        </span>
      ) : (
        <span className="flex items-center gap-1 text-xs text-red-600">
          <AlertCircle className="h-3.5 w-3.5" /> {status === "degraded" ? "Degraded" : "Down"}
        </span>
      )}
    </div>
  );
}

function ConfigItem({
  label,
  description,
  configured,
}: {
  label: string;
  description: string;
  configured: boolean;
}) {
  return (
    <div className="flex items-center justify-between p-3 bg-surface-secondary rounded-xl">
      <div>
        <p className="text-sm font-medium text-text-primary">{label}</p>
        <p className="text-xs text-text-muted">{description}</p>
      </div>
      {configured ? (
        <span className="flex items-center gap-1 text-xs text-green-600">
          <CheckCircle className="h-3.5 w-3.5" /> Configured
        </span>
      ) : (
        <span className="flex items-center gap-1 text-xs text-amber-600">
          <AlertCircle className="h-3.5 w-3.5" /> Not set
        </span>
      )}
    </div>
  );
}

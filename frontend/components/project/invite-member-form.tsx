"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProjectRole, ProjectInvitationCreateRequest } from "@/lib/api";
import { Mail, Shield, User as UserIcon, Eye } from "lucide-react";
import { toast } from "sonner";

interface InviteMemberFormProps {
  onInvite: (data: ProjectInvitationCreateRequest) => Promise<void>;
}

const roleOptions = [
  { value: "admin" as ProjectRole, label: "Admin", icon: Shield, description: "Can manage project members and settings" },
  { value: "member" as ProjectRole, label: "Member", icon: UserIcon, description: "Can create and manage content" },
  { value: "viewer" as ProjectRole, label: "Viewer", icon: Eye, description: "Can view project content only" },
];

export function InviteMemberForm({ onInvite }: InviteMemberFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ProjectRole>("member");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email.trim()) {
      toast.error("Please enter an email address");
      return;
    }

    setIsLoading(true);
    try {
      await onInvite({ email: email.trim(), role });
      setEmail("");
      setRole("member");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center gap-2 mb-6">
        <Mail className="h-5 w-5 text-primary-500" />
        <h3 className="text-lg font-semibold text-text-primary">Invite New Member</h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Email Address"
          type="email"
          placeholder="colleague@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={isLoading}
        />

        <div>
          <label className="block text-sm font-medium text-text-secondary mb-3">
            Role
          </label>
          <div className="space-y-2">
            {roleOptions.map((option) => {
              const Icon = option.icon;
              return (
                <label
                  key={option.value}
                  className={`flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                    role === option.value
                      ? "border-primary-500 bg-primary-50"
                      : "border-surface-tertiary hover:border-primary-200"
                  }`}
                >
                  <input
                    type="radio"
                    name="role"
                    value={option.value}
                    checked={role === option.value}
                    onChange={(e) => setRole(e.target.value as ProjectRole)}
                    className="sr-only"
                    disabled={isLoading}
                  />
                  <Icon className={`h-5 w-5 ${role === option.value ? "text-primary-600" : "text-text-muted"}`} />
                  <div className="flex-1">
                    <p className={`font-medium ${role === option.value ? "text-primary-700" : "text-text-primary"}`}>
                      {option.label}
                    </p>
                    <p className="text-sm text-text-muted">{option.description}</p>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        <div className="pt-2">
          <Button type="submit" isLoading={isLoading} className="w-full">
            Send Invitation
          </Button>
        </div>
      </form>
    </Card>
  );
}

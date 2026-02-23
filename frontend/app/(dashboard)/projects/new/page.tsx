"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ProjectCreateRequest, parseApiError } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft, Building2, Sparkles } from "lucide-react";

function generateSlug(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .substring(0, 50);
}

export default function NewProjectPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState<ProjectCreateRequest>({
    name: "",
    slug: "",
    description: "",
  });
  const [slugManuallyEdited, setSlugManuallyEdited] = useState(false);

  const handleNameChange = (name: string) => {
    setFormData((prev) => ({
      ...prev,
      name,
      slug: slugManuallyEdited ? prev.slug : generateSlug(name),
    }));
  };

  const handleSlugChange = (slug: string) => {
    setSlugManuallyEdited(true);
    setFormData((prev) => ({
      ...prev,
      slug: generateSlug(slug),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      alert("Please enter a project name");
      return;
    }

    if (!formData.slug || formData.slug.length < 3) {
      alert("Slug must be at least 3 characters");
      return;
    }

    setIsLoading(true);
    try {
      const project = await api.projects.create({
        name: formData.name.trim(),
        slug: formData.slug,
        description: formData.description?.trim() || undefined,
      });

      // Redirect to project settings after creation
      router.push(`/projects/${project.id}/settings`);
    } catch (err) {
      const error = parseApiError(err);
      alert(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <Link href="/projects">
          <Button variant="ghost" size="sm" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to Projects
          </Button>
        </Link>
        <div className="mt-4">
          <h1 className="text-2xl font-bold text-text-primary">Create New Project</h1>
          <p className="text-text-secondary mt-1">
            Set up a project workspace to collaborate with others
          </p>
        </div>
      </div>

      {/* Form */}
      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Project Name */}
          <div>
            <Input
              label="Project Name"
              value={formData.name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="My Awesome Project"
              required
              disabled={isLoading}
              helperText="Choose a name that describes your project or organization"
            />
          </div>

          {/* Project Slug */}
          <div>
            <Input
              label="Project Slug"
              value={formData.slug}
              onChange={(e) => handleSlugChange(e.target.value)}
              placeholder="my-awesome-project"
              required
              disabled={isLoading}
              helperText={
                <>
                  This will be used in your project URL. Only lowercase letters, numbers, and hyphens.
                  {!slugManuallyEdited && formData.name && (
                    <span className="flex items-center gap-1 mt-1 text-primary-600">
                      <Sparkles className="h-3 w-3" />
                      Auto-generated from project name
                    </span>
                  )}
                </>
              }
            />
          </div>

          {/* Description (Optional) */}
          <div>
            <Textarea
              label="Description (Optional)"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="A brief description of what your project does"
              rows={3}
              disabled={isLoading}
              helperText="Help project members understand the purpose of this workspace"
            />
          </div>

          {/* Info Box */}
          <div className="p-4 rounded-lg bg-primary-50 border border-primary-200">
            <div className="flex items-start gap-3">
              <Building2 className="h-5 w-5 text-primary-600 mt-0.5" />
              <div>
                <p className="font-medium text-primary-800 mb-1">What happens next?</p>
                <ul className="text-sm text-primary-700 space-y-1 list-disc list-inside">
                  <li>You'll be set as the project owner</li>
                  <li>You can invite members via email</li>
                  <li>Project starts on the Free plan</li>
                  <li>You can customize settings and logo</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4">
            <Link href="/projects">
              <Button variant="outline" type="button" disabled={isLoading}>
                Cancel
              </Button>
            </Link>
            <Button type="submit" isLoading={isLoading}>
              Create Project
            </Button>
          </div>
        </form>
      </Card>

      {/* Tips */}
      <Card className="p-6 bg-surface-secondary border-none">
        <h3 className="font-semibold text-text-primary mb-3">Tips for project success</h3>
        <ul className="space-y-2 text-sm text-text-secondary">
          <li className="flex items-start gap-2">
            <span className="text-primary-500 font-bold">•</span>
            <span>Choose a clear, descriptive project name that everyone will recognize</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-500 font-bold">•</span>
            <span>Add a description to help new members understand your project's purpose</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-500 font-bold">•</span>
            <span>You can always change the name and description later in settings</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-500 font-bold">•</span>
            <span>The slug cannot be changed once created, so choose wisely</span>
          </li>
        </ul>
      </Card>
    </div>
  );
}

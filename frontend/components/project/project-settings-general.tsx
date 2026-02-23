"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Upload, Loader2, Image as ImageIcon } from "lucide-react";
import { Project, ProjectUpdateRequest } from "@/lib/api";
import Image from "next/image";

interface ProjectSettingsGeneralProps {
  project: Project;
  onUpdate: (data: ProjectUpdateRequest) => Promise<void>;
  onUploadLogo: (file: File) => Promise<void>;
}

export function ProjectSettingsGeneral({ project, onUpdate, onUploadLogo }: ProjectSettingsGeneralProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: project.name,
    description: project.description || "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await onUpdate(formData);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith("image/")) {
      alert("Please upload an image file");
      return;
    }

    // Validate file size (max 2MB)
    if (file.size > 2 * 1024 * 1024) {
      alert("File size must be less than 2MB");
      return;
    }

    setIsLoading(true);
    try {
      await onUploadLogo(file);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Project Logo */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4">Project Logo</h3>
        <div className="flex items-center gap-6">
          <div className="h-24 w-24 rounded-xl bg-surface-secondary flex items-center justify-center overflow-hidden border-2 border-surface-tertiary">
            {project.logo_url ? (
              <Image
                src={project.logo_url}
                alt={project.name}
                width={96}
                height={96}
                className="object-cover w-full h-full"
              />
            ) : (
              <ImageIcon className="h-10 w-10 text-text-muted" />
            )}
          </div>
          <div className="flex-1">
            <p className="text-sm text-text-secondary mb-2">
              Upload a logo for your project. PNG, JPG or GIF. Max 2MB.
            </p>
            <label htmlFor="logo-upload">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isLoading}
                onClick={() => document.getElementById("logo-upload")?.click()}
                leftIcon={isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              >
                Upload Logo
              </Button>
            </label>
            <input
              id="logo-upload"
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
              disabled={isLoading}
            />
          </div>
        </div>
      </Card>

      {/* Project Details */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4">Project Details</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Project Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
            disabled={isLoading}
          />

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Project Slug
            </label>
            <Input
              value={project.slug}
              disabled
              helperText="Slug cannot be changed after project creation"
            />
          </div>

          <Textarea
            label="Description (Optional)"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="A brief description of your project"
            rows={3}
            disabled={isLoading}
          />

          <div className="flex justify-end">
            <Button type="submit" isLoading={isLoading}>
              Save Changes
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

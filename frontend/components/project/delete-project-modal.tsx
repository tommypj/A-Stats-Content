"use client";

import { useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertTriangle } from "lucide-react";

interface DeleteProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectName: string;
  onDelete: () => Promise<void>;
}

export function DeleteProjectModal({
  isOpen,
  onClose,
  projectName,
  onDelete,
}: DeleteProjectModalProps) {
  const [confirmText, setConfirmText] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const isConfirmed = confirmText === projectName;

  const handleDelete = async () => {
    if (!isConfirmed) {
      alert("Please type the project name to confirm deletion");
      return;
    }

    setIsLoading(true);
    try {
      await onDelete();
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setConfirmText("");
      onClose();
    }
  };

  return (
    <Dialog isOpen={isOpen} onClose={handleClose} title="Delete Project">
      <div className="space-y-4">
        {/* Warning */}
        <div className="p-4 rounded-lg bg-red-50 border border-red-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium text-red-900 mb-1">Permanent Deletion</p>
              <p className="text-sm text-red-800">
                This action cannot be undone. All project data, including articles, outlines, images, and settings will be permanently deleted. Project members will lose access immediately.
              </p>
            </div>
          </div>
        </div>

        {/* Confirmation Input */}
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Type <span className="font-bold text-text-primary">{projectName}</span> to confirm
          </label>
          <Input
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="Enter project name"
            disabled={isLoading}
            autoComplete="off"
          />
          <p className="text-xs text-text-muted mt-1">
            This is case-sensitive and must match exactly
          </p>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-4">
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            isLoading={isLoading}
            disabled={!isConfirmed}
          >
            Delete Project Forever
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
